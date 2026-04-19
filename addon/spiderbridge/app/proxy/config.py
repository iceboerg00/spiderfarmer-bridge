import json
from pathlib import Path
import yaml

HA_OPTIONS_PATH = "/data/options.json"
HA_DEVICES_PATH = "/data/devices.yaml"


def _default_devices() -> list:
    return [
        {
            "mac": "AABBCCDDEEFF",
            "type": "CB",
            "id": "ggs_1",
            "uid": "",
            "friendly_name": "Spider Farmer GGS",
        }
    ]


def _load_ha_devices() -> list:
    p = Path(HA_DEVICES_PATH)
    if p.exists():
        with open(p) as f:
            return yaml.safe_load(f) or _default_devices()
    return _default_devices()


def _build_config_from_ha_options(options: dict) -> dict:
    return {
        "hotspot": {
            "enabled": options.get("hotspot_enabled", True),
            "ssid": options.get("ssid", "SF-Bridge"),
            "password": options.get("password", "changeme123"),
            "interface": "wlan0",
            "ip": options.get("hotspot_ip", "192.168.10.1"),
            "channel": options.get("channel", 6),
        },
        "proxy": {
            "listen_host": "0.0.0.0",
            "listen_port": 8883,
            "upstream_host": "sf.mqtt.spider-farmer.com",
            "upstream_port": 8883,
            "cert_file": "certs/server.crt",
            "key_file": "certs/server.key",
        },
        "mosquitto": {
            "host": "127.0.0.1",
            "port": 1883,
            "local_user": "",
            "local_password": "",
            "ha_mqtt_password": "",
        },
        "devices": _load_ha_devices(),
    }


def load_config(path: str = "config/config.yaml") -> dict:
    ha_opts = Path(HA_OPTIONS_PATH)
    if ha_opts.exists():
        with open(ha_opts) as f:
            return _build_config_from_ha_options(json.load(f))
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Config not found: {path}")
    with open(p) as f:
        return yaml.safe_load(f)
