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
    assert result["hotspot"]["ssid"] == "TestNet"
    assert result["hotspot"]["enabled"] is True
    assert result["hotspot"]["channel"] == 6


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


def test_save_config_writes_devices_yaml_in_ha_mode(tmp_path, monkeypatch):
    import yaml
    from unittest.mock import MagicMock

    options_file = tmp_path / "options.json"
    options_file.write_text('{"hotspot_enabled": true}')
    devices_file = tmp_path / "devices.yaml"

    monkeypatch.setattr("proxy.config.HA_OPTIONS_PATH", str(options_file))
    monkeypatch.setattr("proxy.config.HA_DEVICES_PATH", str(devices_file))
    monkeypatch.setattr("proxy.mitm_proxy.HA_OPTIONS_PATH", str(options_file))
    monkeypatch.setattr("proxy.mitm_proxy.HA_DEVICES_PATH", str(devices_file))

    from proxy.mitm_proxy import MITMProxy
    proxy_instance = MITMProxy(
        config={"devices": [{"mac": "112233AABBCC", "id": "ggs_1",
                             "type": "CB", "uid": "", "friendly_name": "GGS"}]},
        mqtt_client=MagicMock(),
        config_path=str(tmp_path / "config.yaml"),
    )
    proxy_instance._save_config()

    saved = yaml.safe_load(devices_file.read_text())
    assert saved[0]["mac"] == "112233AABBCC"
