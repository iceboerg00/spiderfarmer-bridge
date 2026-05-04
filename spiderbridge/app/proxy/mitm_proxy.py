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
    MQTT_PUBLISH, MQTT_CONNECT, MQTT_SUBSCRIBE,
)
from .normalizer import normalize_status, fan_extras_topics, light_extras_topics
from ha.discovery import (
    publish_soil_sensor_discovery as _publish_soil_sensor_discovery,
    unpublish_outlet_discovery as _unpublish_outlet_discovery,
)
from .command_handler import translate_command
from .config import HA_OPTIONS_PATH, HA_DEVICES_PATH

logger = logging.getLogger(__name__)

_MAC_PLACEHOLDER = "AABBCCDDEEFF"

# Diagnostic: log the first time we see a non-CB topic prefix so we can find out
# what standalone PS5/PS10/LC controllers actually publish to (they may not use
# CB). Once we know we can extend support deliberately instead of guessing.
_seen_topic_prefixes: set = set()


class ProxySession:
    """Represents one active GGS Controller connection."""

    def __init__(self, device_id: str, mac: str, uid: str,
                 mqtt_client: mqtt.Client):
        self.device_id = device_id
        self.mac = mac
        self.uid = uid
        self.mqtt_client = mqtt_client
        self._upstream_writer: Optional[asyncio.StreamWriter] = None
        self._client_writer: Optional[asyncio.StreamWriter] = None
        self.device_state: Dict[str, dict] = {}  # module → current state from getDevSta
        self.last_nonzero_level: Dict[str, int] = {}  # module → last brightness > 0
        # SF protocol topic-prefix learned from observed cloud→device traffic.
        # Defaults to "CB" (Control Box) but PS5/PS10/LC may use a different
        # value; using the wrong prefix means our injects are silently
        # ignored by the controller that subscribes elsewhere.
        self.down_topic_prefix: str = "CB"
        # Static discovery publishes outlets 1..10 unconditionally; once the
        # controller reports its actual outlet set we unpublish the rest.
        self._outlet_discovery_pruned: bool = False
        # Full last-known fan/blower blocks for app-parity write paths.
        # getDevSta carries only minimal state ({on, level}); cloud
        # setConfigField traffic carries the schedule/cycle/speeds we
        # need to merge against on HA writes.
        self.fan_state: Dict[str, dict] = {}
        # Same idea for light: getDevSta on some firmwares omits
        # modeType, so we cache it from observed setConfigField traffic
        # and from our own injects. Used by the normalizer as a fallback
        # so the HA effect dropdown stays consistent with what the
        # controller is actually doing.
        self.light_state: Dict[str, dict] = {}

    def set_upstream(self, writer: asyncio.StreamWriter) -> None:
        self._upstream_writer = writer

    def set_client(self, writer: asyncio.StreamWriter) -> None:
        self._client_writer = writer

    async def inject(self, payload: dict) -> None:
        """Inject command directly into the device TLS connection."""
        if self._client_writer is None:
            logger.warning("[%s] inject: no device connection", self.device_id)
            return
        topic = f"SF/GGS/{self.down_topic_prefix}/API/DOWN/{self.mac.upper().replace(':', '')}"
        raw = build_publish(
            topic=topic,
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
                    "│  🕷  SpiderBridge — device detected         │\n"
                    "│  MAC: %-38s  │\n"
                    "│  ID:  %-38s  │\n"
                    "│  updating config.yaml...                    │\n"
                    "└─────────────────────────────────────────────┘",
                    mac_clean, dev.get("friendly_name", dev["id"]),
                )
                self._save_config()
                return dev
        return None

    def _save_config(self) -> None:
        """Persist current in-memory config. Under HA OS the addon writes
        only the devices list to /data/devices.yaml (the rest of the addon
        config is read-only options). Standalone falls back to the full
        config.yaml at the configured path."""
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

    async def poll_session_config(self, sess: ProxySession) -> None:
        """Inject one round of getConfigField for light/light2/fan/blower
        into a single session. Called on session connect (immediate poll)
        and periodically by config_poll_loop."""
        for keypath in (["device", "light"], ["device", "light2"],
                        ["device", "fan"], ["device", "blower"]):
            try:
                await sess.inject({
                    "method": "getConfigField",
                    "pid": sess.mac,
                    "params": {"keyPath": keypath},
                    "msgId": str(int(time.time() * 1000)),
                    "uid": sess.uid,
                })
            except Exception as e:
                logger.debug("config poll inject failed for %s: %s",
                             keypath, e)
            # Space out so we don't flood the controller in one burst
            await asyncio.sleep(0.5)

    async def config_poll_loop(self) -> None:
        """Periodically poll every active controller session. Each session
        also gets an immediate one-shot poll on connect (handle_client),
        so this loop only owns the recurring tick.

        Interval is configurable via proxy.config_poll_interval_sec
        (default 600 = 10 minutes). Set to 0 to disable."""
        interval = int(self.config.get("proxy", {}).get("config_poll_interval_sec", 600))
        if interval <= 0:
            logger.info("Config poll disabled (interval=%s)", interval)
            return
        logger.info("Config poll loop started, interval=%ds", interval)
        while True:
            try:
                await asyncio.sleep(interval)
                for sess in list(self._sessions.values()):
                    await self.poll_session_config(sess)
            except asyncio.CancelledError:
                logger.info("Config poll loop stopped")
                break
            except Exception as e:
                logger.warning("Config poll loop error: %s", e)
                await asyncio.sleep(30)

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
                                    device_state=session.device_state, subfield=subfield,
                                    last_nonzero_level=session.last_nonzero_level,
                                    fan_state=session.fan_state,
                                    light_state=session.light_state)
        if payload:
            await session.inject(payload)
            # Optimistic update: write the fan/blower fields to the cache and
            # publish per-field state topics so the new HA entities reflect
            # the change without waiting for the next observed cloud echo.
            params = payload.get("params", {})
            for k in ("fan", "blower"):
                blk = params.get(k)
                if isinstance(blk, dict):
                    session.fan_state[k] = blk
                    for tpc, val in fan_extras_topics(session.device_id, k, blk).items():
                        self.mqtt_client.publish(tpc, val, retain=True)
            # Same for light — and refresh the main state/light JSON so
            # the HA effect dropdown reflects the new mode immediately
            # rather than waiting for the next getDevSta (which on some
            # firmwares does not even carry modeType).
            for k in ("light", "light2"):
                blk = params.get(k)
                if isinstance(blk, dict):
                    session.light_state[k] = blk
                    refreshed = normalize_status(
                        session.device_id, {"data": {k: blk}},
                        light_cache=session.light_state,
                    )
                    for tpc, val in refreshed.items():
                        self.mqtt_client.publish(tpc, val, retain=True)

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
                    logger.warning("Unknown device client_id=%s — session marked as unknown", client_id)
                    sid = f"unknown_{client_id.replace(':', '')}"
                    s = ProxySession(sid, client_id, "", self.mqtt_client)
                else:
                    s = ProxySession(dev["id"], dev["mac"], dev.get("uid", ""),
                                     self.mqtt_client)
                s.set_upstream(upstream_writer)
                s.set_client(client_writer)
                self._sessions[s.device_id] = s
                s.publish_availability("online")
                logger.info("Session erstellt: device_id=%s mac=%s", s.device_id, s.mac)
                # Immediate one-shot config poll so HA caches refresh on
                # restart/reconnect rather than waiting for the next 10-min
                # tick. Detached so the connect path doesn't block on it.
                async def _initial_poll():
                    # Small delay so the controller has finished its CONNECT
                    # handshake before we start firing extra requests at it.
                    await asyncio.sleep(3)
                    await self.poll_session_config(s)
                asyncio.create_task(_initial_poll())
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
                            elif pkt.packet_type == MQTT_SUBSCRIBE and pkt.topics:
                                # Learn the controller's DOWN topic prefix
                                # immediately from its SUBSCRIBE — no SF App
                                # interaction or cloud command needed.
                                sess = nonlocal_session[0]
                                if sess is not None:
                                    for t in pkt.topics:
                                        parts = t.split("/")
                                        if (len(parts) >= 6 and parts[0] == "SF"
                                                and parts[1] == "GGS"
                                                and parts[3] == "API"
                                                and parts[4] == "DOWN"
                                                and parts[2]):
                                            new_prefix = parts[2]
                                            if sess.down_topic_prefix != new_prefix:
                                                logger.info(
                                                    "[%s] DOWN topic prefix learned from SUBSCRIBE: %s (was %s)",
                                                    sess.device_id, new_prefix,
                                                    sess.down_topic_prefix,
                                                )
                                                sess.down_topic_prefix = new_prefix
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
                                    # Learn the cloud's DOWN topic prefix so our
                                    # injects target the same one (PS5/PS10 may
                                    # not be CB).
                                    sess = nonlocal_session[0]
                                    if sess is not None:
                                        topic_parts = p.topic.split("/")
                                        if len(topic_parts) >= 6 and topic_parts[2]:
                                            new_prefix = topic_parts[2]
                                            if sess.down_topic_prefix != new_prefix:
                                                logger.info(
                                                    "[%s] DOWN topic prefix learned: %s (was %s)",
                                                    sess.device_id, new_prefix,
                                                    sess.down_topic_prefix,
                                                )
                                                sess.down_topic_prefix = new_prefix
                                    try:
                                        body = json.loads(p.message)
                                    except Exception:
                                        continue
                                    if body.get("method") != "setConfigField":
                                        continue
                                    params = body.get("params", {})
                                    keypath = params.get("keyPath", [])
                                    if "outlet" in keypath:
                                        logger.debug(
                                            "SF→device outlet command: topic=%s keyPath=%s params=%s",
                                            p.topic, keypath,
                                            json.dumps(params, separators=(',', ':')),
                                        )
                                    # Fan feature-parity capture: log every
                                    # cloud-side setConfigField for fan/blower
                                    # at INFO level on this branch so we can
                                    # reverse-engineer the SF App's fan
                                    # settings screen field-by-field.
                                    if "fan" in keypath or "blower" in keypath:
                                        logger.info(
                                            "[FAN-CAPTURE] keyPath=%s params=%s",
                                            keypath,
                                            json.dumps(params, separators=(',', ':')),
                                        )
                                        sess = nonlocal_session[0]
                                        if sess is not None:
                                            for k in ("fan", "blower"):
                                                if k in keypath and isinstance(params.get(k), dict):
                                                    sess.fan_state[k] = params[k]
                                                    for tpc, val in fan_extras_topics(
                                                            sess.device_id, k, params[k]).items():
                                                        self.mqtt_client.publish(tpc, val, retain=True)
                                    if "light" in keypath or "light2" in keypath:
                                        sess = nonlocal_session[0]
                                        if sess is not None:
                                            for k in ("light", "light2"):
                                                if k in keypath and isinstance(params.get(k), dict):
                                                    sess.light_state[k] = params[k]
                                                    # Also push the per-field
                                                    # extras so HA settings
                                                    # entities populate even
                                                    # without a getDevSta echo.
                                                    for tpc, val in light_extras_topics(
                                                            sess.device_id, k, params[k]).items():
                                                        self.mqtt_client.publish(tpc, val, retain=True)
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
    method = data.get("method")
    # Accept any UP message that carries a data block — getDevSta is the
    # main one, but getConfigField responses (when the controller honors
    # them) come through here too. Setup-Acks without payload data fall
    # through harmlessly because their "data" dict has no module blocks.
    if method not in ("getDevSta", "getConfigField"):
        return
    if method == "getConfigField":
        logger.info("[CONFIG-RESP] data=%s",
                    json.dumps(data.get("data", {}), separators=(',', ':'))[:500])

    # Keep UID up to date from controller messages
    uid = data.get("uid", "")
    if uid and session.uid != uid:
        session.uid = uid

    # Store current module states for use in commands
    d = data.get("data", {})
    for module in ("light", "light2", "blower", "fan", "heater", "humidifier", "dehumidifier"):
        if module in d:
            # Merge instead of replace — getDevSta on some firmwares carries
            # only {on, level} for light/fan, which would wipe cached fields
            # (modeType, schedule, etc) we need to keep.
            session.device_state.setdefault(module, {}).update(d[module])
    # Also feed light/fan caches from rich UP messages (getConfigField
    # responses, full setConfigField echoes). Same merge semantics so
    # minimal getDevSta echoes don't clobber the cached schedule/cycle.
    for module in ("light", "light2"):
        if module in d and isinstance(d[module], dict):
            session.light_state.setdefault(module, {}).update(d[module])
    for module in ("fan", "blower"):
        if module in d and isinstance(d[module], dict):
            session.fan_state.setdefault(module, {}).update(d[module])

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

    # Prune outlet discovery once per session: static discovery publishes
    # 1..10 unconditionally; remove the ones the actual hardware does not
    # have so HA stops showing ghost switches.
    if not session._outlet_discovery_pruned:
        outlet_block = d.get("outlet", {})
        if isinstance(outlet_block, dict) and outlet_block:
            present = {
                int(k[1:]) for k in outlet_block.keys()
                if isinstance(k, str) and k.startswith("O") and k[1:].isdigit()
            }
            if present:
                for n in range(1, 11):
                    if n not in present:
                        _unpublish_outlet_discovery(mqtt_client, session.device_id, n)
                logger.info("[%s] Outlet discovery pruned to %s",
                            session.device_id, sorted(present))
                session._outlet_discovery_pruned = True

    normalized = normalize_status(
        session.device_id, data,
        light_cache=getattr(session, "light_state", None),
        fan_cache=getattr(session, "fan_state", None),
    )
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
