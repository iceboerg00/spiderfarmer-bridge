from dataclasses import dataclass
from typing import List, Optional, Tuple

MQTT_CONNECT = 1
MQTT_CONNACK = 2
MQTT_PUBLISH = 3
MQTT_PUBACK = 4
MQTT_SUBSCRIBE = 8
MQTT_SUBACK = 9
MQTT_PINGREQ = 12
MQTT_PINGRESP = 13
MQTT_DISCONNECT = 14


@dataclass
class MQTTPacket:
    packet_type: int
    flags: int
    payload: bytes           # raw remaining bytes
    topic: Optional[str] = None       # PUBLISH only
    message: Optional[bytes] = None   # PUBLISH only
    qos: int = 0                      # PUBLISH only
    retain: bool = False              # PUBLISH only
    packet_id: Optional[int] = None   # PUBLISH QoS>0 only
    client_id: Optional[str] = None   # CONNECT only
    topics: Optional[List[str]] = None  # SUBSCRIBE only — list of topic filters


def _decode_remaining_length(data: bytes, offset: int) -> Tuple[int, int]:
    """Decode MQTT variable-length integer. Returns (value, new_offset).
    Raises ValueError on incomplete data."""
    multiplier = 1
    value = 0
    while True:
        if offset >= len(data):
            raise ValueError("Incomplete remaining length")
        byte = data[offset]
        offset += 1
        value += (byte & 0x7F) * multiplier
        multiplier *= 128
        if not (byte & 0x80):
            break
        if multiplier > 128 * 128 * 128:
            raise ValueError("Malformed remaining length")
    return value, offset


def _encode_remaining_length(value: int) -> bytes:
    """Encode integer as MQTT variable-length bytes."""
    result = []
    while True:
        digit = value % 128
        value //= 128
        if value > 0:
            digit |= 0x80
        result.append(digit)
        if value == 0:
            break
    return bytes(result)


def parse_packets(buf: bytes) -> Tuple[List[MQTTPacket], bytes]:
    """Parse all complete MQTT packets from buf.
    Returns (packets, remaining_bytes_not_yet_complete)."""
    packets: List[MQTTPacket] = []
    offset = 0

    while offset < len(buf):
        start = offset
        first_byte = buf[offset]
        packet_type = (first_byte >> 4) & 0x0F
        flags = first_byte & 0x0F
        offset += 1

        try:
            remaining_length, offset = _decode_remaining_length(buf, offset)
        except ValueError:
            return packets, buf[start:]

        if offset + remaining_length > len(buf):
            return packets, buf[start:]

        raw_payload = buf[offset: offset + remaining_length]
        offset += remaining_length

        pkt = MQTTPacket(packet_type=packet_type, flags=flags, payload=raw_payload)

        if packet_type == MQTT_PUBLISH:
            _parse_publish_fields(pkt, flags, raw_payload)
        elif packet_type == MQTT_CONNECT:
            _parse_connect_fields(pkt, raw_payload)
        elif packet_type == MQTT_SUBSCRIBE:
            _parse_subscribe_fields(pkt, raw_payload)

        packets.append(pkt)

    return packets, b''


def _parse_publish_fields(pkt: MQTTPacket, flags: int, raw: bytes) -> None:
    qos = (flags >> 1) & 0x03
    retain = bool(flags & 0x01)
    p = 0
    if len(raw) < 2:
        return
    topic_len = (raw[p] << 8) | raw[p + 1]
    p += 2
    if p + topic_len > len(raw):
        return
    topic = raw[p: p + topic_len].decode("utf-8", errors="replace")
    p += topic_len
    if qos > 0:
        if p + 2 > len(raw):
            return
        pkt.packet_id = (raw[p] << 8) | raw[p + 1]
        p += 2
    pkt.topic = topic
    pkt.message = raw[p:]
    pkt.qos = qos
    pkt.retain = retain


def _parse_connect_fields(pkt: MQTTPacket, raw: bytes) -> None:
    """Extract client_id from MQTT 3.1.1 CONNECT payload."""
    try:
        p = 10  # 2 (name len) + 4 ("MQTT") + 1 (level) + 1 (flags) + 2 (keepalive)
        id_len = (raw[p] << 8) | raw[p + 1]
        p += 2
        pkt.client_id = raw[p: p + id_len].decode("utf-8", errors="replace")
    except (IndexError, Exception):
        pkt.client_id = None


def _parse_subscribe_fields(pkt: MQTTPacket, raw: bytes) -> None:
    """Extract topic filters from a SUBSCRIBE payload.

    Variable header: 2-byte packet ID. Payload: list of (topic_filter_len: 2,
    topic_filter: utf-8, requested_qos: 1)."""
    if len(raw) < 2:
        return
    p = 2  # skip packet ID
    topics: List[str] = []
    while p < len(raw):
        if p + 2 > len(raw):
            break
        tlen = (raw[p] << 8) | raw[p + 1]
        p += 2
        if p + tlen > len(raw):
            break
        try:
            topics.append(raw[p:p + tlen].decode("utf-8", errors="replace"))
        except Exception:
            pass
        p += tlen + 1  # skip the requested-QoS byte
    pkt.topics = topics


def build_publish(topic: str, message: bytes, qos: int = 0, retain: bool = False,
                  packet_id: int = 1) -> bytes:
    """Build a MQTT PUBLISH packet."""
    topic_bytes = topic.encode("utf-8")
    var_header = bytes([len(topic_bytes) >> 8, len(topic_bytes) & 0xFF]) + topic_bytes
    if qos > 0:
        var_header += bytes([packet_id >> 8, packet_id & 0xFF])
    remaining = var_header + message
    flags = (qos << 1)
    if retain:
        flags |= 0x01
    first_byte = (MQTT_PUBLISH << 4) | flags
    return bytes([first_byte]) + _encode_remaining_length(len(remaining)) + remaining
