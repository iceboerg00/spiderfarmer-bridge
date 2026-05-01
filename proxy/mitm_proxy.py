import asyncio
import json
import logging
import ssl
import time
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

# Diagnostic: log the first time we see a non-CB topic prefix so we can find out
# what standalone PS5/PS10/LC controllers actually publish to (they may not use
# CB). Once we know we can extend support deliberately instead of guessing.
_seen_topic_prefixes: set = set()


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
        self.last_nonzero_level: Dict[str, int] = {}  # module → last brightness > 0
        # msgId → Future, resolved when the device's UP response carries the
        # same msgId. Used by request_config to await getConfigField replies.
        self.pending_requests: Dict[str, "asyncio.Future[dict]"] = {}
        self._msg_counter: int = 0

    def _next_msg_id(self) -> str:
        self._msg_counter += 1
        return f"{int(time.time() * 1000)}{self._msg_counter:04d}"

    async def request_config(self, key_path: list, timeout: float = 3.0) -> dict:
        """Send a getConfigField request to the controller and await the
        response data. Returns the `data` dict from the UP reply, or raises
        TimeoutError if the controller does not respond in time."""
        msg_id = self._next_msg_id()
        payload = {
            "method": "getConfigField",
            "pid": self.mac,
            "params": {"keyPath": key_path},
            "msgId": msg_id,
            "uid": self.uid,
        }
        loop = asyncio.get_event_loop()
        future: "asyncio.Future[dict]" = loop.create_future()
        self.pending_requests[msg_id] = future
        try:
            await self.inject(payload)
            return await asyncio.wait_for(future, timeout=timeout)
        finally:
            self.pending_requests.pop(msg_id, None)

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

        # PS5/PS10 outlets need the complete current per-outlet block sent
        # back, not a synthetic skeleton. Actively fetch the controller's
        # current config via getConfigField so the merge in translate_command
        # has every field (cycleTime, timePeriod, wateringEnv, bind, …).
        # If the request fails or times out, fall through with empty state —
        # translate_command then emits a minimal payload (works for CB,
        # ignored on PS5/PS10 but at least no crash).
        outlet_state: Optional[dict] = None
        if outlet_num is not None:
            ok = f"O{outlet_num}"
            try:
                data = await session.request_config(["outlet", ok], timeout=3.0)
                if isinstance(data, dict):
                    block = data.get(ok, data)
                    if isinstance(block, dict) and block:
                        outlet_state = {ok: block}
            except asyncio.TimeoutError:
                logger.warning("[%s] getConfigField timeout for %s", session.device_id, ok)
            except Exception as e:
                logger.warning("[%s] getConfigField error for %s: %s",
                               session.device_id, ok, e)

        payload = translate_command(field, value, session.mac, session.uid, outlet_num,
                                    device_state=session.device_state, subfield=subfield,
                                    last_nonzero_level=session.last_nonzero_level,
                                    outlet_state=outlet_state)
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
                # Forward server→device traffic unchanged. Earlier we parsed
                # packets here and mutated setConfigField bodies to keep HA's
                # last command sticky against the SF cloud's corrections, but
                # that fought legitimate app/cloud commands and made the lamp
                # uncontrollable except from bluetooth-paired sessions.
                # Diagnostic-only parsing here logs outlet-related commands
                # from the SF cloud/app so we can compare what the official
                # app sends vs what we send for PS5/PS10 outlet control.
                buf_down = b""
                try:
                    while True:
                        try:
                            data = await upstream_reader.read(4096)
                        except Exception:
                            break
                        if not data:
                            break
                        # Forward bytes unchanged FIRST, then try to parse for logging
                        try:
                            client_writer.write(data)
                            await client_writer.drain()
                        except Exception:
                            break
                        try:
                            buf_down += data
                            packets, buf_down = parse_packets(buf_down)
                            for p in packets:
                                if (p.packet_type == MQTT_PUBLISH and p.topic
                                        and "/API/DOWN/" in p.topic and p.message):
                                    try:
                                        body = json.loads(p.message)
                                    except Exception:
                                        continue
                                    if body.get("method") != "setConfigField":
                                        continue
                                    params = body.get("params", {})
                                    keypath = params.get("keyPath", [])
                                    if "outlet" in keypath:
                                        logger.info(
                                            "[DIAG] SF→device outlet command: keyPath=%s params=%s",
                                            keypath, json.dumps(params, separators=(',', ':')),
                                        )
                        except Exception as e:
                            # Never let logging break the relay
                            logger.debug("relay_down parse error (non-fatal): %s", e)
                            buf_down = b""
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
    # SF protocol: SF/GGS/{prefix}/API/UP/{MAC}. CB is the prefix observed for
    # the Control Box, but standalone PS5/PS10/LC controllers may use a
    # different prefix. Accept any prefix and log the first sighting of each
    # non-CB one so we can add explicit support if needed.
    parts = pkt.topic.split("/")
    if (len(parts) < 6 or parts[0] != "SF" or parts[1] != "GGS"
            or parts[3] != "API" or parts[4] != "UP"):
        return
    prefix = parts[2]
    if prefix != "CB" and prefix not in _seen_topic_prefixes:
        _seen_topic_prefixes.add(prefix)
        logger.info("New SF topic prefix observed: %s (topic=%s)", prefix, pkt.topic)
    try:
        data = json.loads(pkt.message)
    except Exception:
        return

    # Resolve any pending request whose response carries the same msgId.
    # Done before the method gate so that getConfigField (and other) replies
    # land in their futures even though we only fully process getDevSta below.
    msg_id = data.get("msgId")
    if msg_id and msg_id in session.pending_requests:
        future = session.pending_requests[msg_id]
        if not future.done():
            future.set_result(data.get("data", {}))

    method = data.get("method")
    if method != "getDevSta":
        return

    # Keep UID up to date from controller messages
    uid = data.get("uid", "")
    if uid and session.uid != uid:
        session.uid = uid

    # Store current module states for use in commands
    d = data.get("data", {})
    for module in ("light", "light2", "blower", "fan", "heater", "humidifier", "dehumidifier"):
        if module in d:
            session.device_state[module] = d[module]

    # Remember last non-zero brightness so OFF→ON restores the previous level
    for module in ("light", "light2"):
        if module in d:
            lvl = d[module].get("level", d[module].get("mLevel", 0))
            if isinstance(lvl, (int, float)) and lvl > 0:
                session.last_nonzero_level[module] = int(lvl)

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
