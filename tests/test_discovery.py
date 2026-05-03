import json

from ha.discovery import (
    publish_discovery_for_device,
    publish_soil_sensor_discovery,
    unpublish_outlet_discovery,
)

CFG = {"friendly_name": "Test GGS"}


def _publish_calls(mock_client):
    """Return {topic: parsed_payload} from all client.publish() calls."""
    out = {}
    for call in mock_client.publish.call_args_list:
        topic = call.args[0]
        out[topic] = json.loads(call.args[1])
    return out


def test_publish_discovery_emits_air_sensors(mocker):
    client = mocker.MagicMock()
    publish_discovery_for_device(client, "ggs_1", CFG)
    pubs = _publish_calls(client)

    temp = pubs["homeassistant/sensor/spiderfarmer_ggs_1_temperature/config"]
    assert temp["device_class"] == "temperature"
    assert temp["unit_of_measurement"] == "°C"
    assert temp["state_topic"] == "spiderfarmer/ggs_1/state/temperature"

    co2 = pubs["homeassistant/sensor/spiderfarmer_ggs_1_co2/config"]
    assert co2["device_class"] == "carbon_dioxide"
    assert co2["unit_of_measurement"] == "ppm"

    ppfd = pubs["homeassistant/sensor/spiderfarmer_ggs_1_ppfd/config"]
    assert "device_class" not in ppfd  # no HA device class for PPFD
    assert ppfd["unit_of_measurement"] == "µmol/m²/s"


def test_publish_discovery_emits_lights_with_effect_list(mocker):
    client = mocker.MagicMock()
    publish_discovery_for_device(client, "ggs_1", CFG)
    pubs = _publish_calls(client)

    light = pubs["homeassistant/light/spiderfarmer_ggs_1_light/config"]
    assert light["schema"] == "json"
    assert light["brightness"] is True
    assert light["brightness_scale"] == 100
    assert light["effect_list"] == ["Manual", "Schedule", "PPFD"]
    assert light["command_topic"] == "spiderfarmer/ggs_1/command/light/set"

    assert "homeassistant/light/spiderfarmer_ggs_1_light2/config" in pubs


def test_publish_discovery_emits_fans_with_correct_speed_ranges(mocker):
    client = mocker.MagicMock()
    publish_discovery_for_device(client, "ggs_1", CFG)
    pubs = _publish_calls(client)

    blower = pubs["homeassistant/fan/spiderfarmer_ggs_1_blower/config"]
    assert blower["speed_range_max"] == 100
    assert blower["percentage_command_topic"] == "spiderfarmer/ggs_1/command/blower/percentage/set"

    fan = pubs["homeassistant/fan/spiderfarmer_ggs_1_fan/config"]
    assert fan["speed_range_max"] == 10


def test_publish_discovery_emits_accessory_switches(mocker):
    client = mocker.MagicMock()
    publish_discovery_for_device(client, "ggs_1", CFG)
    pubs = _publish_calls(client)

    for module in ("heater", "humidifier", "dehumidifier"):
        topic = f"homeassistant/switch/spiderfarmer_ggs_1_{module}/config"
        sw = pubs[topic]
        assert sw["payload_on"] == "ON"
        assert sw["payload_off"] == "OFF"
        assert sw["command_topic"] == f"spiderfarmer/ggs_1/command/{module}/set"


def test_publish_discovery_default_outlet_count_is_10(mocker):
    client = mocker.MagicMock()
    publish_discovery_for_device(client, "ggs_1", CFG)
    pubs = _publish_calls(client)

    for i in range(1, 11):
        assert f"homeassistant/switch/spiderfarmer_ggs_1_outlet_{i}/config" in pubs
    assert "homeassistant/switch/spiderfarmer_ggs_1_outlet_11/config" not in pubs


def test_publish_discovery_outlet_count_configurable(mocker):
    client = mocker.MagicMock()
    cfg = dict(CFG, outlets=4)
    publish_discovery_for_device(client, "ggs_1", cfg)
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
    # Main entities live on the GGS controller; Fan Circulation settings
    # entities live on three sub-devices (Schedule Mode, Cycle Mode, Speeds)
    # linked back via via_device.
    client = mocker.MagicMock()
    publish_discovery_for_device(client, "ggs_1", CFG)
    pubs = _publish_calls(client)

    seen = {tuple(p["device"]["identifiers"]) for p in pubs.values()}
    assert ("spiderfarmer_ggs_1",) in seen
    sub_ids = {ids for ids in seen if ids != ("spiderfarmer_ggs_1",)}
    assert sub_ids == {
        ("spiderfarmer_ggs_1_fan_schedule",),
        ("spiderfarmer_ggs_1_fan_cycle",),
        ("spiderfarmer_ggs_1_fan_speeds",),
    }

    for p in pubs.values():
        ids = tuple(p["device"]["identifiers"])
        assert p["device"]["manufacturer"] == "Spider Farmer"
        if ids == ("spiderfarmer_ggs_1",):
            assert p["device"]["model"] == "GGS Controller"
            assert p["device"]["name"] == "Test GGS"
        else:
            assert p["device"]["via_device"] == "spiderfarmer_ggs_1"


def test_unpublish_outlet_discovery_sends_empty_retained_payload(mocker):
    # HA removes a discovered entity when an empty retained payload is
    # published to its config topic. The proxy uses this to prune the
    # 1..10 outlets the static publisher emits down to the actual count
    # the controller reports.
    client = mocker.MagicMock()
    unpublish_outlet_discovery(client, "ggs_1", 7)
    client.publish.assert_called_once_with(
        "homeassistant/switch/spiderfarmer_ggs_1_outlet_7/config",
        "",
        retain=True,
    )


def test_publish_soil_sensor_discovery_emits_three_entities(mocker):
    client = mocker.MagicMock()
    sensor_id = "3839383705306F29"
    publish_soil_sensor_discovery(client, "ggs_1", sensor_id, CFG)
    pubs = _publish_calls(client)

    assert len(pubs) == 3
    short = sensor_id[-8:].upper()  # "05306F29"

    temp_topic = f"homeassistant/sensor/spiderfarmer_ggs_1_soil_{sensor_id}_temp/config"
    assert temp_topic in pubs
    assert pubs[temp_topic]["device_class"] == "temperature"
    assert short in pubs[temp_topic]["name"]

    ec_topic = f"homeassistant/sensor/spiderfarmer_ggs_1_soil_{sensor_id}_ec/config"
    assert ec_topic in pubs
    assert "device_class" not in pubs[ec_topic]
    assert pubs[ec_topic]["unit_of_measurement"] == "mS/cm"


def test_publish_discovery_emits_fan_preset_modes(mocker):
    client = mocker.MagicMock()
    publish_discovery_for_device(client, "ggs_1", CFG)
    pubs = _publish_calls(client)

    fan = pubs["homeassistant/fan/spiderfarmer_ggs_1_fan/config"]
    assert fan["preset_mode_state_topic"] == "spiderfarmer/ggs_1/state/fan/mode_label"
    assert fan["preset_mode_command_topic"] == "spiderfarmer/ggs_1/command/fan/preset_mode/set"
    assert "Manual" in fan["preset_modes"]
    assert "Schedule" in fan["preset_modes"]
    assert "Cycle" in fan["preset_modes"]
    assert "Environment: Prioritize temperature" in fan["preset_modes"]
    assert len(fan["preset_modes"]) == 8


def test_publish_discovery_emits_fan_extras(mocker):
    client = mocker.MagicMock()
    publish_discovery_for_device(client, "ggs_1", CFG)
    topics = {call.args[0] for call in client.publish.call_args_list}

    # Schedule Mode sub-device
    assert "homeassistant/text/spiderfarmer_ggs_1_fan_schedule_start/config" in topics
    assert "homeassistant/text/spiderfarmer_ggs_1_fan_schedule_end/config" in topics
    # Cycle Mode sub-device
    assert "homeassistant/text/spiderfarmer_ggs_1_fan_cycle_start/config" in topics
    assert "homeassistant/number/spiderfarmer_ggs_1_fan_cycle_run_minutes/config" in topics
    assert "homeassistant/number/spiderfarmer_ggs_1_fan_cycle_off_minutes/config" in topics
    assert "homeassistant/number/spiderfarmer_ggs_1_fan_cycle_times/config" in topics
    # Speeds sub-device
    assert "homeassistant/number/spiderfarmer_ggs_1_fan_schedule_speed/config" in topics
    assert "homeassistant/number/spiderfarmer_ggs_1_fan_standby_speed/config" in topics
    assert "homeassistant/number/spiderfarmer_ggs_1_fan_oscillation_level/config" in topics
    # Natural wind on main device (switch)
    assert "homeassistant/switch/spiderfarmer_ggs_1_fan_natural_wind/config" in topics


def test_fan_extras_grouped_into_sub_devices(mocker):
    client = mocker.MagicMock()
    publish_discovery_for_device(client, "ggs_1", CFG)
    pubs = _publish_calls(client)

    # Schedule fields → Schedule Mode sub-device
    ss = pubs["homeassistant/text/spiderfarmer_ggs_1_fan_schedule_start/config"]
    assert ss["device"]["identifiers"] == ["spiderfarmer_ggs_1_fan_schedule"]
    assert ss["device"]["via_device"] == "spiderfarmer_ggs_1"

    # Cycle fields → Cycle Mode sub-device
    cr = pubs["homeassistant/number/spiderfarmer_ggs_1_fan_cycle_run_minutes/config"]
    assert cr["device"]["identifiers"] == ["spiderfarmer_ggs_1_fan_cycle"]
    assert cr["unit_of_measurement"] == "min"
    assert cr["max"] == 1440

    # Cycle times max 100 (controller cap)
    ct = pubs["homeassistant/number/spiderfarmer_ggs_1_fan_cycle_times/config"]
    assert ct["max"] == 100

    # Speed fields → Speeds sub-device
    sp = pubs["homeassistant/number/spiderfarmer_ggs_1_fan_schedule_speed/config"]
    assert sp["device"]["identifiers"] == ["spiderfarmer_ggs_1_fan_speeds"]
    assert sp["min"] == 1 and sp["max"] == 10

    # Natural wind lives on the Speeds sub-device — same group as the
    # other "applies across all modes" fan settings.
    nw = pubs["homeassistant/switch/spiderfarmer_ggs_1_fan_natural_wind/config"]
    assert nw["device"]["identifiers"] == ["spiderfarmer_ggs_1_fan_speeds"]
