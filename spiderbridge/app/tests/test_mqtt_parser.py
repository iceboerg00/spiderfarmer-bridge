import pytest
from proxy.mqtt_parser import (
    parse_packets, build_publish,
    MQTT_PUBLISH, MQTT_CONNECT, MQTT_PINGREQ,
)


def _raw_publish(topic: str, payload: bytes, qos: int = 0) -> bytes:
    """Helper: build minimal raw MQTT PUBLISH packet (QoS 0)."""
    tb = topic.encode()
    remaining = bytes([len(tb) >> 8, len(tb) & 0xFF]) + tb + payload
    rl = len(remaining)
    assert rl < 128, "use only for small test packets"
    return bytes([(MQTT_PUBLISH << 4), rl]) + remaining


def _raw_pingreq() -> bytes:
    return bytes([(MQTT_PINGREQ << 4), 0])


def test_parse_single_publish():
    raw = _raw_publish("ggs/CB/AABB/sensors", b'{"temp":22.5}')
    packets, leftover = parse_packets(raw)
    assert len(packets) == 1
    pkt = packets[0]
    assert pkt.packet_type == MQTT_PUBLISH
    assert pkt.topic == "ggs/CB/AABB/sensors"
    assert pkt.message == b'{"temp":22.5}'
    assert leftover == b''


def test_parse_incomplete_returns_leftover():
    raw = _raw_publish("a/b", b'hello')
    incomplete = raw[:-3]
    packets, leftover = parse_packets(incomplete)
    assert packets == []
    assert leftover == incomplete


def test_parse_two_packets():
    raw = _raw_publish("a/b", b'1') + _raw_publish("c/d", b'2')
    packets, leftover = parse_packets(raw)
    assert len(packets) == 2
    assert packets[0].topic == "a/b"
    assert packets[1].topic == "c/d"
    assert leftover == b''


def test_parse_non_publish_passes_through():
    raw = _raw_pingreq()
    packets, leftover = parse_packets(raw)
    assert len(packets) == 1
    assert packets[0].packet_type == MQTT_PINGREQ
    assert packets[0].topic is None


def test_build_publish_roundtrip():
    topic = "spiderfarmer/ggs_1/command/blower_speed/set"
    message = b"5"
    raw = build_publish(topic, message)
    packets, _ = parse_packets(raw)
    assert len(packets) == 1
    assert packets[0].topic == topic
    assert packets[0].message == message


def test_parse_retain_flag():
    tb = b"t"
    remaining = bytes([0, 1]) + tb + b"v"
    flags = 0x01  # retain=1, QoS=0
    raw = bytes([(MQTT_PUBLISH << 4) | flags, len(remaining)]) + remaining
    packets, _ = parse_packets(raw)
    assert packets[0].retain is True


def test_parse_empty_buffer():
    packets, leftover = parse_packets(b'')
    assert packets == []
    assert leftover == b''


def test_parse_connect_client_id():
    """Test that CONNECT packet client_id is correctly extracted."""
    cid = "AABBCCDDEEFF"
    cid_bytes = cid.encode()
    # MQTT 3.1.1: name_len(2) + "MQTT"(4) + level(1) + flags(1) + keepalive(2)
    var_header = b'\x00\x04MQTT\x04\x02\x00\x3c'
    payload = bytes([0, len(cid_bytes)]) + cid_bytes
    remaining = var_header + payload
    raw = bytes([(MQTT_CONNECT << 4), len(remaining)]) + remaining
    packets, leftover = parse_packets(raw)
    assert len(packets) == 1
    assert packets[0].packet_type == MQTT_CONNECT
    assert packets[0].client_id == cid
    assert leftover == b''


def test_parse_large_publish_multi_byte_remaining_length():
    """Packets with payload > 127 bytes use multi-byte VLI remaining length."""
    topic = "ggs/CB/AABB/status"
    # 200-byte payload — remaining length will be > 127, requiring 2-byte VLI
    message = b'{"data":{"sensor":{"temp":24.5}}}' + b'x' * 167
    raw = build_publish(topic, message)
    packets, leftover = parse_packets(raw)
    assert len(packets) == 1
    assert packets[0].topic == topic
    assert packets[0].message == message
    assert leftover == b''


def test_build_publish_retain():
    raw = build_publish("spiderfarmer/ggs_1/availability", b"online", retain=True)
    packets, _ = parse_packets(raw)
    assert packets[0].retain is True
    assert packets[0].topic == "spiderfarmer/ggs_1/availability"
    assert packets[0].message == b"online"


def _raw_subscribe(topic_filters):
    """Helper: build raw MQTT SUBSCRIBE packet for one or more topic filters."""
    from proxy.mqtt_parser import MQTT_SUBSCRIBE
    payload = bytes([0x00, 0x01])  # packet ID = 1
    for tf in topic_filters:
        tb = tf.encode()
        payload += bytes([len(tb) >> 8, len(tb) & 0xFF]) + tb + bytes([0x00])  # qos 0
    rl = len(payload)
    assert rl < 128
    # SUBSCRIBE packet has flags=0x02 (reserved bits)
    return bytes([(MQTT_SUBSCRIBE << 4) | 0x02, rl]) + payload


def test_parse_subscribe_extracts_topic_filters():
    raw = _raw_subscribe(["SF/GGS/PS/API/DOWN/AABBCCDDEEFF"])
    packets, leftover = parse_packets(raw)
    assert len(packets) == 1
    assert packets[0].topics == ["SF/GGS/PS/API/DOWN/AABBCCDDEEFF"]
    assert leftover == b""


def test_parse_subscribe_handles_multiple_filters():
    raw = _raw_subscribe([
        "SF/GGS/CB/API/DOWN/AABB",
        "SF/GGS/CB/API/UP/AABB",
    ])
    packets, _ = parse_packets(raw)
    assert packets[0].topics == [
        "SF/GGS/CB/API/DOWN/AABB",
        "SF/GGS/CB/API/UP/AABB",
    ]
