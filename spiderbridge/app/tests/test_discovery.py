import json

from ha.discovery import publish_discovery_for_device, publish_soil_sensor_discovery

CFG = {"friendly_name": "Test GGS"}


def _publish_calls(mock_client):
    return {call.args[0]: json.loads(call.args[1]) for call in mock_client.publish.call_args_list}


def test_publish_discovery_emits_air_sensors(mocker):
    # NOTE: this add-on copy of ha/discovery.py only declares temp/humi/vpd —
    # CO2/PPFD were added to the standalone copy in c1ba20c but not here.
    # The integration (spiderbridge/integration/spiderbridge/sensor.py) covers
    # CO2/PPFD for Option A users via the custom integration directly.
    client = mocker.MagicMock()
    publish_discovery_for_device(client, "ggs_1", CFG)
    pubs = _publish_calls(client)

    temp = pubs["homeassistant/sensor/spiderfarmer_ggs_1_temperature/config"]
    assert temp["device_class"] == "temperature"
    assert temp["unit_of_measurement"] == "°C"

    humi = pubs["homeassistant/sensor/spiderfarmer_ggs_1_humidity/config"]
    assert humi["device_class"] == "humidity"

    vpd = pubs["homeassistant/sensor/spiderfarmer_ggs_1_vpd/config"]
    assert "device_class" not in vpd
    assert vpd["unit_of_measurement"] == "kPa"


def test_publish_discovery_emits_lights_with_effect_list(mocker):
    client = mocker.MagicMock()
    publish_discovery_for_device(client, "ggs_1", CFG)
    pubs = _publish_calls(client)

    light = pubs["homeassistant/light/spiderfarmer_ggs_1_light/config"]
    assert light["schema"] == "json"
    assert light["brightness"] is True
    assert light["brightness_scale"] == 100
    assert light["effect_list"] == ["Modus: Manual / Timer", "Modus: PPFD"]
    assert "homeassistant/light/spiderfarmer_ggs_1_light2/config" in pubs


def test_publish_discovery_emits_fans_with_correct_speed_ranges(mocker):
    client = mocker.MagicMock()
    publish_discovery_for_device(client, "ggs_1", CFG)
    pubs = _publish_calls(client)

    blower = pubs["homeassistant/fan/spiderfarmer_ggs_1_blower/config"]
    assert blower["speed_range_max"] == 100

    fan = pubs["homeassistant/fan/spiderfarmer_ggs_1_fan/config"]
    assert fan["speed_range_max"] == 10


def test_publish_discovery_emits_accessory_switches(mocker):
    client = mocker.MagicMock()
    publish_discovery_for_device(client, "ggs_1", CFG)
    pubs = _publish_calls(client)

    for module in ("heater", "humidifier", "dehumidifier"):
        topic = f"homeassistant/switch/spiderfarmer_ggs_1_{module}/config"
        assert pubs[topic]["payload_on"] == "ON"
        assert pubs[topic]["command_topic"] == f"spiderfarmer/ggs_1/command/{module}/set"


def test_publish_discovery_default_outlet_count_is_10(mocker):
    client = mocker.MagicMock()
    publish_discovery_for_device(client, "ggs_1", CFG)
    pubs = _publish_calls(client)
    for i in range(1, 11):
        assert f"homeassistant/switch/spiderfarmer_ggs_1_outlet_{i}/config" in pubs
    assert "homeassistant/switch/spiderfarmer_ggs_1_outlet_11/config" not in pubs


def test_publish_discovery_outlet_count_configurable(mocker):
    client = mocker.MagicMock()
    publish_discovery_for_device(client, "ggs_1", dict(CFG, outlets=4))
    pubs = _publish_calls(client)
    assert "homeassistant/switch/spiderfarmer_ggs_1_outlet_4/config" in pubs
    assert "homeassistant/switch/spiderfarmer_ggs_1_outlet_5/config" not in pubs


def test_publish_discovery_emits_soil_avg_sensors(mocker):
    client = mocker.MagicMock()
    publish_discovery_for_device(client, "ggs_1", CFG)
    pubs = _publish_calls(client)

    for field, dc, unit in [
        ("temp_soil", "temperature", "°C"),
        ("humi_soil", "humidity",    "%"),
        ("ec_soil",   None,          "mS/cm"),
    ]:
        topic = f"homeassistant/sensor/spiderfarmer_ggs_1_{field}/config"
        p = pubs[topic]
        assert p["unit_of_measurement"] == unit
        if dc:
            assert p["device_class"] == dc
        else:
            assert "device_class" not in p


def test_publish_discovery_uses_retain_for_every_message(mocker):
    client = mocker.MagicMock()
    publish_discovery_for_device(client, "ggs_1", CFG)
    for call in client.publish.call_args_list:
        assert call.kwargs.get("retain") is True


def test_publish_discovery_device_info_consistent(mocker):
    client = mocker.MagicMock()
    publish_discovery_for_device(client, "ggs_1", CFG)
    pubs = _publish_calls(client)

    seen = {tuple(p["device"]["identifiers"]) for p in pubs.values()}
    assert seen == {("spiderfarmer_ggs_1",)}

    for p in pubs.values():
        assert p["device"]["manufacturer"] == "Spider Farmer"
        assert p["device"]["model"] == "GGS Controller"


def test_publish_soil_sensor_discovery_emits_three_entities(mocker):
    client = mocker.MagicMock()
    sensor_id = "3839383705306F29"
    publish_soil_sensor_discovery(client, "ggs_1", sensor_id, CFG)
    pubs = _publish_calls(client)

    assert len(pubs) == 3
    short = sensor_id[-8:].upper()

    temp_topic = f"homeassistant/sensor/spiderfarmer_ggs_1_soil_{sensor_id}_temp/config"
    assert pubs[temp_topic]["device_class"] == "temperature"
    assert short in pubs[temp_topic]["name"]

    ec_topic = f"homeassistant/sensor/spiderfarmer_ggs_1_soil_{sensor_id}_ec/config"
    assert "device_class" not in pubs[ec_topic]
    assert pubs[ec_topic]["unit_of_measurement"] == "mS/cm"
