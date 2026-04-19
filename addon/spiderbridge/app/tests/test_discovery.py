import json
from ha.discovery import (
    build_sensor_discovery,
    build_number_discovery,
    build_switch_discovery,
    publish_discovery_for_device,
)

CFG = {"friendly_name": "Test GGS", "mac": "AABBCC"}


def test_sensor_temperature():
    topic, payload = build_sensor_discovery("ggs_1", "temperature", CFG)
    assert topic == "homeassistant/sensor/spiderfarmer_ggs_1_temperature/config"
    assert payload["device_class"] == "temperature"
    assert payload["unit_of_measurement"] == "°C"
    assert payload["state_topic"] == "spiderfarmer/ggs_1/state/temperature"
    assert payload["availability_topic"] == "spiderfarmer/ggs_1/availability"
    assert payload["unique_id"] == "spiderfarmer_ggs_1_temperature"
    assert payload["device"]["identifiers"] == ["spiderfarmer_ggs_1"]
    assert payload["device"]["manufacturer"] == "Spider Farmer"


def test_sensor_vpd_no_device_class():
    _, payload = build_sensor_discovery("ggs_1", "vpd", CFG)
    assert "device_class" not in payload
    assert payload["unit_of_measurement"] == "kPa"


def test_sensor_co2_device_class():
    _, payload = build_sensor_discovery("ggs_1", "co2", CFG)
    assert payload["device_class"] == "carbon_dioxide"
    assert payload["unit_of_measurement"] == "ppm"


def test_number_blower():
    topic, payload = build_number_discovery("ggs_1", "blower_speed", 0, 10, CFG)
    assert topic == "homeassistant/number/spiderfarmer_ggs_1_blower_speed/config"
    assert payload["min"] == 0
    assert payload["max"] == 10
    assert payload["step"] == 1
    assert payload["command_topic"] == "spiderfarmer/ggs_1/command/blower_speed/set"
    assert payload["state_topic"] == "spiderfarmer/ggs_1/state/blower_speed"


def test_switch_heater():
    topic, payload = build_switch_discovery("ggs_1", "heater", CFG)
    assert topic == "homeassistant/switch/spiderfarmer_ggs_1_heater/config"
    assert payload["payload_on"] == "ON"
    assert payload["payload_off"] == "OFF"
    assert payload["command_topic"] == "spiderfarmer/ggs_1/command/heater/set"


def test_all_sensor_topics_unique():
    topics = {build_sensor_discovery("ggs_1", f, CFG)[0]
               for f in ["temperature", "humidity", "vpd", "co2", "ppfd"]}
    assert len(topics) == 5


def test_publish_discovery_calls_client(mocker):
    mock_client = mocker.MagicMock()
    publish_discovery_for_device(mock_client, "ggs_1", CFG)
    # Must publish at least 9 entities (5 sensors + 4 numbers + core switches)
    assert mock_client.publish.call_count >= 9
    # All calls must use retain=True
    for call in mock_client.publish.call_args_list:
        args = call.args
        kwargs = call.kwargs
        retain_value = kwargs.get("retain", args[2] if len(args) > 2 else None)
        assert retain_value is True
