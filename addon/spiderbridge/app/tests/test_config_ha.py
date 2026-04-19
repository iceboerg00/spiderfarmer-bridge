import json
from pathlib import Path
from unittest.mock import patch
import proxy.config as cfg_module


def test_load_config_uses_ha_options_when_options_json_exists(tmp_path):
    options = {
        "hotspot_enabled": True,
        "ssid": "TestNet",
        "password": "secret123",
        "channel": 6,
        "hotspot_ip": "192.168.10.1",
        "device_name": "GGS Test",
    }
    (tmp_path / "options.json").write_text(json.dumps(options))

    with patch.object(cfg_module, "HA_OPTIONS_PATH", str(tmp_path / "options.json")), \
         patch.object(cfg_module, "HA_DEVICES_PATH", str(tmp_path / "devices.yaml")):
        result = cfg_module.load_config()

    assert result["proxy"]["upstream_host"] == "sf.mqtt.spider-farmer.com"
    assert result["mosquitto"]["host"] == "127.0.0.1"
    assert result["devices"][0]["mac"] == "AABBCCDDEEFF"


def test_load_config_falls_back_to_yaml_when_no_options_json(tmp_path):
    yaml_file = tmp_path / "config.yaml"
    yaml_file.write_text(
        "proxy:\n  listen_port: 8883\n"
        "mosquitto:\n  host: 127.0.0.1\n  port: 1883\n"
        "devices: []\n"
    )

    with patch.object(cfg_module, "HA_OPTIONS_PATH", str(tmp_path / "nonexistent.json")):
        result = cfg_module.load_config(str(yaml_file))

    assert result["proxy"]["listen_port"] == 8883


def test_load_config_merges_persisted_devices(tmp_path):
    options = {
        "hotspot_enabled": True,
        "ssid": "TestNet",
        "password": "secret",
        "channel": 6,
        "hotspot_ip": "192.168.10.1",
        "device_name": "GGS",
    }
    (tmp_path / "options.json").write_text(json.dumps(options))
    (tmp_path / "devices.yaml").write_text(
        "- {mac: AABBCC112233, type: CB, id: ggs_1, uid: '', friendly_name: GGS}\n"
    )

    with patch.object(cfg_module, "HA_OPTIONS_PATH", str(tmp_path / "options.json")), \
         patch.object(cfg_module, "HA_DEVICES_PATH", str(tmp_path / "devices.yaml")):
        result = cfg_module.load_config()

    assert result["devices"][0]["mac"] == "AABBCC112233"
