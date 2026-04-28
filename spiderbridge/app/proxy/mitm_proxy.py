import asyncio
import json
import logging
import ssl
from pathlib import Path
from typing import Dict, Optional

import paho.mqtt.client as mqtt
import yaml

from .mqtt_parser import (
    parse_packets, build_publish,
    MQTT_PUBLISH, MQTT_CONNECT, MQTT_CONNACK,
)
from .normalizer import normalize_status
from ha.discovery import publish_soil_sensor_discovery as _publish_soil_sensor_discovery
from .command_handler import translate_command

from .config import HA_OPTIONS_PATH, HA_DEVICES_PATH

logger = logging.getLogger(__name__)

_MAC_PLACEHOLDER = "AABBCCDDEEFF"

# Wait at most this long for the cloud's CONNACK to be relayed back to the
# controller before injecting a DOWN PUBLISH. Without this gate, commands
# arriving during the controller's MQTT CONNECTING phase make it drop the
# TLS connection — which produced a HA-driven reconnect loop in the wild.
INJECT_READY_TIMEOUT = 5.0


class ProxySession:
    """Represents one active GGS Controller connection."""

    def __init__(self, device_id: str, mac: str, uid: str, mqtt_client: mqtt.Client):
        self.device_id = device_id
        self.mac = mac
        self.uid = uid
        self.mqtt_client = mqtt_client
        self._upstream_writer: Optional[asyncio.StreamWriter] = None
        self._client_writer: Optional[asyncio.StreamWriter] = None
        self.device_state: Dict[str, dict] = {}  # module → current state from getDevSta
        self.ha_overrides: Dict[str, dict] = {}  # module → {field: value} to enforce
        # Set once the cloud's CONNACK has been observed in relay_down — until
        # then, inject() must hold its packets back.
        self._ready: asyncio.Event = asyncio.Event()

    def set_upstream(self, writer: asyncio.StreamWriter) -> None:
        self._upstream_writer = writer

    def set_client(self, writer: asyncio.StreamWriter) -> None:
        self._client_writer = writer

    async def inject(self, payload: dict) -> None:
        """Inject command directly into the device TLS connection."""
        if self._client_writer is None:
            logger.warning("[%s] inject: no device connection", self.device_id)
            return
        try:
            await asyncio.wait_for(self._ready.wait(), timeout=INJECT_READY_TIMEOUT)
        except asyncio.TimeoutError:
            logger.warning("[%s] inject: upstream CONNACK not seen within %.1fs — dropping command",
                           self.device_id, INJECT_READY_TIMEOUT)
            return
        raw = build_publish(
            topic=f"SF/GGS/CB/API/DOWN/{self.mac.upper().replace(':', '')}",
            message=json.dumps(payload, separators=(',', ':')).encode(),
        )
        try:
            self._client_writer.write(raw)
            await self._client_writer.drain()
            logger.info("[%s] Command injected: %s", self.device_id, payload.get("params", {}))
        except Exception as e:
            logger.error("[%s] inject error: %s", self.device_id, e)

    def publish_availability(self, status: str) -> None:
        self.mqtt_client.publish(
            f"spiderfarmer/{self.device_id}/availability",
            status,
            retain=True,
        )


class MITMProxy:
    def __init__(self, config: dict, mqtt_client: mqtt.Client, config_path: str = "config/config.yaml"):
        self.config = config
        self.mqtt_client = mqtt_client
        self._config_path = config_path
        self._sessions: Dict[str, ProxySession] = {}
        self._known_soil_ids: Dict[str, set] = {}  # device_id → set of seen sensor IDs

    def build_server_ssl_ctx(self) -> ssl.SSLContext:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(
            certfile=self.config["proxy"]["cert_file"],
            keyfile=self.config["proxy"]["key_file"],
        )
        return ctx

    def _build_upstream_ssl_ctx(self) -> ssl.SSLContext:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = True
        ctx.verify_mode = ssl.CERT_REQUIRED
        # SF MQTT server uses a private CA — not in system trust store
        ctx.load_verify_locations(cafile="certs/ca.crt")
        # Present client certificate for mTLS authentication with the real SF server
        ctx.load_cert_chain(
            certfile=self.config["proxy"]["cert_file"],
            keyfile=self.config["proxy"]["key_file"],
        )
        return ctx

    def _find_device_by_mac(self, mac: str) -> Optional[dict]:
        mac_clean = mac.upper().replace(":", "")
        for d in self.config.get("devices", []):
            if d["mac"].upper().replace(":", "") == mac_clean:
                return d
        return None

    def _find_device_by_id(self, device_id: str) -> Optional[dict]:
        for d in self.config.get("devices", []):
            if d["id"] == device_id:
                return d
        return None

    def _auto_detect_mac(self, mac: str) -> Optional[dict]:
        """If a device has the placeholder MAC, replace it with the detected MAC and persist."""
        mac_clean = mac.upper().replace(":", "")
        for dev in self.config.get("devices", []):
            if dev["mac"].upper().replace(":", "") == _MAC_PLACEHOLDER:
                dev["mac"] = mac_clean
                logger.info(
                    "┌─────────────────────────────────────────────┐\n"
                    "│  🕷  SpiderBridge — Gerät erkannt           │\n"
                    "│  MAC: %-38s  │\n"
                    "│  ID:  %-38s  │\n"
                    "│  config.yaml wird aktualisiert...           │\n"
                    "└─────────────────────────────────────────────┘",
                    mac_clean, dev.get("friendly_name", dev["id"]),
                )
                self._save_config()
                return dev
        return None

    def _save_config(self) -> None:
        if Path(HA_OPTIONS_PATH).exists():
            try:
                with open(HA_DEVICES_PATH, "w") as f:
                    yaml.dump(self.config.get("devices", []), f)
                logger.info("/data/devices.yaml aktualisiert.")
            except Exception as e:
                logger.error("Fehler beim Speichern von /data/devices.yaml: %s", e)
        else:
            try:
                with open(self._config_path, "w") as f:
                    yaml.dump(self.config, f, default_flow_style=False, allow_unicode=True)
                logger.info("config.yaml aktualisiert.")
            except Exception as e:
                logger.error("Fehler beim Speichern von config.yaml: %s", e)

    async def handle_command(self, topic: str, value: str) -> None:
        """Handle an incoming HA command from local Mosquitto."""
        # topic: spiderfarmer/{device_id}/command/{field}[/{subfield}]/set
        parts = topic.split("/")
        if len(parts) < 5:
            return
        device_id = parts[1]
        field = parts[3]
        subfield = parts[4] if len(parts) >= 6 and parts[4] != "set" else None

        session = self._sessions.get(device_id)
        if session is None:
            logger.warning("Command for %s but no active session", device_id)
            return

        outlet_num = None
        if field.startswith("outlet_") and field[7:].isdigit():
            outlet_num = int(field[7:])

        payload = translate_command(field, value, session.mac, session.uid, outlet_num,
                                    device_state=session.device_state, subfield=subfield)
        if payload:
            # Store override so relay_down can enforce it against server corrections
            params = payload.get("params", {})
            key_path = params.get("keyPath", [])
            if len(key_path) == 2:
                module = key_path[1]
                module_data = params.get(module, {})
                session.ha_overrides.setdefault(module, {}).update(module_data)
            await session.inject(payload)

    async def handle_client(
        self,
        client_reader: asyncio.StreamReader,
        client_writer: asyncio.StreamWriter,
    ) -> None:
        peer = client_writer.get_extra_info("peername")
        logger.info("New connection from %s", peer)
        upstream_writer = None
        nonlocal_session = [None]

        try:
            ssl_ctx = self._build_upstream_ssl_ctx()
            upstream_reader, upstream_writer = await asyncio.open_connection(
                self.config["proxy"]["upstream_host"],
                self.config["proxy"]["upstream_port"],
                ssl=ssl_ctx,
                server_hostname=self.config["proxy"]["upstream_host"],
            )

            async def on_connect_packet(client_id: str) -> ProxySession:
                dev = self._find_device_by_mac(client_id)
                if dev is None:
                    # Try auto-detecting: replace placeholder MAC with real one
                    dev = self._auto_detect_mac(client_id)
                if dev is None:
                    logger.warning("Unbekanntes Gerät client_id=%s — Session als unknown", client_id)
                    sid = f"unknown_{client_id.replace(':', '')}"
                    s = ProxySession(sid, client_id, "", self.mqtt_client)
                else:
                    s = ProxySession(dev["id"], dev["mac"], dev.get("uid", ""), self.mqtt_client)
                s.set_upstream(upstream_writer)
                s.set_client(client_writer)
                self._sessions[s.device_id] = s
                s.publish_availability("online")
                logger.info("Session erstellt: device_id=%s mac=%s", s.device_id, s.mac)
                return s

            async def relay_up():
                buf = b""
                try:
                    while True:
                        try:
                            data = await client_reader.read(4096)
                        except Exception:
                            break
                        if not data:
                            break
                        buf += data
                        packets, buf = parse_packets(buf)
                        for pkt in packets:
                            if pkt.packet_type == MQTT_CONNECT and pkt.client_id:
                                nonlocal_session[0] = await on_connect_packet(pkt.client_id)
                            elif pkt.packet_type == MQTT_PUBLISH:
                                if nonlocal_session[0]:
                                    dev_cfg = self._find_device_by_id(nonlocal_session[0].device_id) or {}
                                    _process_publish(nonlocal_session[0], pkt, self.mqtt_client,
                                                     self._known_soil_ids, dev_cfg)
                        try:
                            upstream_writer.write(data)
                            await upstream_writer.drain()
                        except Exception:
                            break
                finally:
                    # Signal EOF to upstream so relay_down unblocks
                    try:
                        upstream_writer.close()
                    except Exception:
                        pass

            async def relay_down():
                buf_down = b""
                try:
                    while True:
                        try:
                            data = await upstream_reader.read(4096)
                        except Exception:
                            break
                        if not data:
                            break
                        buf_down += data
                        pkts_down, buf_down = parse_packets(buf_down)
                        session = nonlocal_session[0]
                        if session is not None and not session._ready.is_set():
                            for p in pkts_down:
                                if p.packet_type == MQTT_CONNACK:
                                    session._ready.set()
                                    logger.debug("[%s] upstream CONNACK observed — inject path open",
                                                 session.device_id)
                                    break
                        out = _apply_overrides_to_packets(pkts_down, data, session)
                        try:
                            client_writer.write(out)
                            await client_writer.drain()
                        except Exception:
                            break
                finally:
                    # Signal EOF to client so relay_up unblocks if upstream disconnects first
                    try:
                        client_writer.close()
                    except Exception:
                        pass

            await asyncio.gather(relay_up(), relay_down())

        except ssl.SSLError as e:
            logger.warning("TLS MITM failed (%s) — transparent TCP relay fallback", e)
            await _tcp_relay_fallback(
                client_reader, client_writer,
                self.config["proxy"]["upstream_host"],
                self.config["proxy"]["upstream_port"],
            )
        except Exception as e:
            logger.error("Connection error from %s: %s", peer, e)
        finally:
            s = nonlocal_session[0]
            if s:
                s.publish_availability("offline")
                self._sessions.pop(s.device_id, None)
            if upstream_writer:
                try:
                    upstream_writer.close()
                except Exception:
                    pass
            try:
                client_writer.close()
            except Exception:
                pass
            logger.info("Connection from %s closed", peer)


def _process_publish(session: ProxySession, pkt, mqtt_client: mqtt.Client,
                     known_soil_ids: dict, device_cfg: dict) -> None:
    """Normalize a PUBLISH from controller and republish locally."""
    if pkt.topic is None or pkt.message is None:
        return
    # SF protocol: SF/GGS/CB/API/UP/{MAC}
    if not pkt.topic.startswith("SF/GGS/CB/API/UP/"):
        return
    try:
        data = json.loads(pkt.message)
    except Exception:
        return
    method = data.get("method")
    if method != "getDevSta":
        return

    # Keep UID up to date from controller messages
    uid = data.get("uid", "")
    if uid and session.uid != uid:
        session.uid = uid

    # Store current module states for use in commands
    d = data.get("data", {})
    for module in ("light", "blower", "fan", "heater", "humidifier", "dehumidifier"):
        if module in d:
            session.device_state[module] = d[module]

    # Publish discovery for newly seen soil sensor IDs
    seen = known_soil_ids.setdefault(session.device_id, set())
    for s in data.get("data", {}).get("sensors", []):
        sid = s.get("id")
        if sid and sid != "avg" and sid not in seen:
            seen.add(sid)
            _publish_soil_sensor_discovery(mqtt_client, session.device_id, sid, device_cfg)

    normalized = normalize_status(session.device_id, data)
    for norm_topic, value in normalized.items():
        mqtt_client.publish(norm_topic, value, retain=True)


def _apply_overrides_to_packets(pkts, raw_data: bytes, session) -> bytes:
    """Intercept SERVER→DEVICE packets and apply HA overrides to setConfigField."""
    if not pkts or session is None or not session.ha_overrides:
        return raw_data
    modified = False
    out_parts = []
    for p in pkts:
        if p.packet_type == MQTT_PUBLISH and p.message:
            try:
                body = json.loads(p.message)
            except Exception:
                body = None
            if body and body.get("method") == "setConfigField":
                params = body.get("params", {})
                key_path = params.get("keyPath", [])
                if len(key_path) == 2:
                    module = key_path[1]
                    if module in session.ha_overrides:
                        params.setdefault(module, {}).update(session.ha_overrides[module])
                        body["params"] = params
                        new_msg = json.dumps(body, separators=(',', ':')).encode()
                        out_parts.append(build_publish(
                            p.topic or "", new_msg, p.qos, p.retain,
                            p.packet_id or 1,
                        ))
                        logger.info("[%s] Override applied to server setConfigField: %s",
                                    session.device_id, session.ha_overrides.get(module))
                        modified = True
                        continue
        # Rebuild non-modified packets from raw payload
        first_byte = (p.packet_type << 4) | p.flags
        from .mqtt_parser import _encode_remaining_length
        out_parts.append(bytes([first_byte]) + _encode_remaining_length(len(p.payload)) + p.payload)
    if not modified:
        return raw_data
    return b"".join(out_parts)


async def _tcp_relay_fallback(
    client_reader: asyncio.StreamReader,
    client_writer: asyncio.StreamWriter,
    upstream_host: str,
    upstream_port: int,
) -> None:
    """
    Called when upstream TLS connection fails (e.g. certificate verification error).

    A transparent TCP relay is not feasible here because:
    1. The upstream server (sf.mqtt.spider-farmer.com:8883) is TLS-only
    2. The GGS Controller has already completed a TLS handshake with our server cert

    If cert pinning is the issue (controller rejects our cert), the failure happens
    before handle_client is called, not here. An SSLError here means the upstream
    connection failed — check TROUBLESHOOTING.md.

    We close both connections cleanly and let the controller reconnect.
    """
    logger.warning(
        "Upstream TLS failed — closing connection. "
        "Check TROUBLESHOOTING.md if this persists. "
        "Host: %s:%s", upstream_host, upstream_port
    )
    try:
        client_writer.close()
    except Exception:
        pass
