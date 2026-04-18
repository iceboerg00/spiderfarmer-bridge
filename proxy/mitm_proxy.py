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
    MQTT_PUBLISH, MQTT_CONNECT,
)
from .normalizer import normalize_status
from ha.discovery import publish_soil_sensor_discovery as _publish_soil_sensor_discovery
from .command_handler import translate_command

logger = logging.getLogger(__name__)

_MAC_PLACEHOLDER = "AABBCCDDEEFF"


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

    def set_upstream(self, writer: asyncio.StreamWriter) -> None:
        self._upstream_writer = writer

    def set_client(self, writer: asyncio.StreamWriter) -> None:
        self._client_writer = writer

    async def inject(self, payload: dict) -> None:
        """Inject command directly into the device TLS connection."""
        if self._client_writer is None:
            logger.warning("[%s] inject: no device connection", self.device_id)
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
                    "│  AUTO-DETECT: MAC erkannt → %-14s  │\n"
                    "│  Gerät: %-35s  │\n"
                    "│  config.yaml wird aktualisiert...           │\n"
                    "└─────────────────────────────────────────────┘",
                    mac_clean, dev.get("friendly_name", dev["id"]),
                )
                self._save_config()
                return dev
        return None

    def _save_config(self) -> None:
        """Persist current in-memory config back to config.yaml."""
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
                            if pkt.packet_type == MQTT_PUBLISH and pkt.topic:
                                import json as _json
                                try:
                                    body = _json.loads(pkt.message)
                                    method = body.get("method")
                                    if method in ("setConfigField", "getDevSta", "getSysSta"):
                                        logger.info("DEVICE→SERVER %s uid=%s params=%s", method, body.get("uid"), str(body.get("params", body.get("data", {})))[:200])
                                    else:
                                        logger.info("DEVICE→SERVER method=%s", method)
                                except Exception:
                                    pass
                            elif pkt.packet_type != MQTT_CONNECT:
                                logger.info("DEVICE→SERVER pkt_type=%d", pkt.packet_type)
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
                        for p in pkts_down:
                            logger.info("SERVER→DEVICE pkt_type=%d qos=%d topic=%s payload=%s",
                                        p.packet_type, p.qos, p.topic,
                                        p.message[:500] if p.message else None)
                        try:
                            client_writer.write(data)
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
