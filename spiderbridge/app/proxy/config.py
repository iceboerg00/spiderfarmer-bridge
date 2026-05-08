import json
import logging
from pathlib import Path
import yaml

logger = logging.getLogger(__name__)

HA_OPTIONS_PATH = "/data/options.json"
HA_DEVICES_PATH = "/data/devices.yaml"
HA_MQTT_PATH = "/data/mqtt.json"  # written by cont-init/02b-mqtt-discovery


# Hardcoded so HA generates entity_ids with a "ggs_*" prefix consistently
# across both install paths — required for the Lovelace card to find
# the entities. Renaming would silently break <ggs-card>.
GGS_FRIENDLY_NAME = "GGS"


def _default_devices() -> list:
    return [
        {
            "mac": "AABBCCDDEEFF",
            "type": "CB",
            "id": "ggs_1",
            "uid": "",
            "friendly_name": GGS_FRIENDLY_NAME,
        }
    ]


def _load_ha_devices() -> list:
    p = Path(HA_DEVICES_PATH)
    if p.exists():
        try:
            with open(p) as f:
                return yaml.safe_load(f) or _default_devices()
        except yaml.YAMLError as e:
            logger.warning("Corrupt devices.yaml, using defaults: %s", e)
    return _default_devices()


def _load_ha_mqtt() -> dict:
    """Return MQTT broker config written by cont-init/02b-mqtt-discovery.

    When Supervisor has an external MQTT service (e.g. the official
    Mosquitto add-on), the cont-init script writes its host/port/creds
    to ``/data/mqtt.json``. If the file is absent we fall back to the
    addon-local Mosquitto on 127.0.0.1:1883.
    """
    p = Path(HA_MQTT_PATH)
    if p.exists():
        try:
            with open(p) as f:
                data = json.load(f)
            return {
                "host": data.get("host", "127.0.0.1"),
                "port": int(data.get("port", 1883)),
                "username": data.get("username", "") or "",
                "password": data.get("password", "") or "",
            }
        except (json.JSONDecodeError, OSError, ValueError) as e:
            logger.warning("Could not read %s, using local Mosquitto: %s", HA_MQTT_PATH, e)
    return {"host": "127.0.0.1", "port": 1883, "username": "", "password": ""}


def _build_config_from_ha_options(options: dict) -> dict:
    mqtt = _load_ha_mqtt()
    return {
        "hotspot": {
            "enabled": options.get("hotspot_enabled", True),
            "ssid": options.get("ssid", "SF-Bridge"),
            "password": options.get("password", "changeme123"),
            # wlan0 and the SF upstream host are fixed for this add-on (single-purpose design)
            "interface": "wlan0",
            "ip": options.get("hotspot_ip", "192.168.10.1"),
            "channel": options.get("channel", 6),
        },
        "proxy": {
            "listen_host": "0.0.0.0",
            "listen_port": 8883,
            # wlan0 and the SF upstream host are fixed for this add-on (single-purpose design)
            "upstream_host": "sf.mqtt.spider-farmer.com",
            "upstream_port": 8883,
            "cert_file": "certs/server.crt",
            "key_file": "certs/server.key",
        },
        "mosquitto": {
            "host": mqtt["host"],
            "port": mqtt["port"],
            "local_user": mqtt["username"],
            "local_password": mqtt["password"],
            "ha_mqtt_password": "",
        },
        "devices": _load_ha_devices(),
    }


def load_config(path: str = "config/config.yaml") -> dict:
    """Return the application config dict.

    In HA mode (when HA_OPTIONS_PATH exists), reads /data/options.json and
    merges with persisted device MACs from HA_DEVICES_PATH. The ``path``
    argument is ignored in this case.

    In standalone mode, loads and returns the YAML file at ``path``.
    Raises FileNotFoundError if that file does not exist.
    """
    ha_opts = Path(HA_OPTIONS_PATH)
    if ha_opts.exists():
        with open(ha_opts) as f:
            return _build_config_from_ha_options(json.load(f))
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Config not found: {path}")
    with open(p) as f:
        return yaml.safe_load(f)
