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
    # linked back via via_device. Light 1 adds two more sub-devices
    # (Schedule Mode, PPFD Mode).
    client = mocker.MagicMock()
    publish_discovery_for_device(client, "ggs_1", CFG)
    pubs = _publish_calls(client)

    seen = {tuple(p["device"]["identifiers"]) for p in pubs.values()}
    assert ("spiderfarmer_ggs_1",) in seen
    sub_ids = {ids for ids in seen if ids != ("spiderfarmer_ggs_1",)}
    assert sub_ids == {
        ("spiderfarmer_ggs_1_fan_schedule",),
        ("spiderfarmer_ggs_1_fan_cycle",),
        ("spiderfarmer_ggs_1_fan_env",),
        ("spiderfarmer_ggs_1_fan_speeds",),
        ("spiderfarmer_ggs_1_blower_schedule",),
        ("spiderfarmer_ggs_1_blower_cycle",),
        ("spiderfarmer_ggs_1_blower_env",),
        ("spiderfarmer_ggs_1_blower_speeds",),
        ("spiderfarmer_ggs_1_light_schedule",),
        ("spiderfarmer_ggs_1_light_ppfd",),
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


def test_publish_discovery_emits_light_extras(mocker):
    client = mocker.MagicMock()
    publish_discovery_for_device(client, "ggs_1", CFG)
    topics = {call.args[0] for call in client.publish.call_args_list}

    # Schedule Mode sub-device
    assert "homeassistant/number/spiderfarmer_ggs_1_light_schedule_brightness/config" in topics
    assert "homeassistant/text/spiderfarmer_ggs_1_light_schedule_start/config" in topics
    assert "homeassistant/text/spiderfarmer_ggs_1_light_schedule_end/config" in topics
    assert "homeassistant/number/spiderfarmer_ggs_1_light_fade_minutes/config" in topics
    # PPFD Mode sub-device
    assert "homeassistant/number/spiderfarmer_ggs_1_light_ppfd_target/config" in topics
    assert "homeassistant/number/spiderfarmer_ggs_1_light_ppfd_min/config" in topics
    assert "homeassistant/number/spiderfarmer_ggs_1_light_ppfd_max/config" in topics
    assert "homeassistant/text/spiderfarmer_ggs_1_light_ppfd_start/config" in topics
    assert "homeassistant/text/spiderfarmer_ggs_1_light_ppfd_end/config" in topics
    assert "homeassistant/number/spiderfarmer_ggs_1_light_ppfd_fade_minutes/config" in topics
    # Temperaturschutz appears under BOTH sub-devices with distinct uids
    assert "homeassistant/number/spiderfarmer_ggs_1_light_dim_threshold_schedule/config" in topics
    assert "homeassistant/number/spiderfarmer_ggs_1_light_off_threshold_schedule/config" in topics
    assert "homeassistant/number/spiderfarmer_ggs_1_light_dim_threshold_ppfd/config" in topics
    assert "homeassistant/number/spiderfarmer_ggs_1_light_off_threshold_ppfd/config" in topics


def test_light_extras_grouped_into_sub_devices(mocker):
    client = mocker.MagicMock()
    publish_discovery_for_device(client, "ggs_1", CFG)
    pubs = _publish_calls(client)

    # Schedule fields → Schedule Mode sub-device
    sb = pubs["homeassistant/number/spiderfarmer_ggs_1_light_schedule_brightness/config"]
    assert sb["device"]["identifiers"] == ["spiderfarmer_ggs_1_light_schedule"]
    assert sb["device"]["via_device"] == "spiderfarmer_ggs_1"
    assert sb["min"] == 0 and sb["max"] == 100
    assert sb["unit_of_measurement"] == "%"

    # PPFD fields → PPFD Mode sub-device
    pt = pubs["homeassistant/number/spiderfarmer_ggs_1_light_ppfd_target/config"]
    assert pt["device"]["identifiers"] == ["spiderfarmer_ggs_1_light_ppfd"]
    assert pt["max"] == 1000
    assert pt["unit_of_measurement"] == "µmol/m²/s"


def test_light_temperaturschutz_appears_in_both_sub_devices_same_topics(mocker):
    # Per user request, dim/off thresholds belong in both Schedule and PPFD
    # cards (they apply in both modes). The two HA entities have distinct
    # unique_ids but identical state/command topics so a single change
    # keeps them in sync.
    client = mocker.MagicMock()
    publish_discovery_for_device(client, "ggs_1", CFG)
    pubs = _publish_calls(client)

    dim_sched = pubs["homeassistant/number/spiderfarmer_ggs_1_light_dim_threshold_schedule/config"]
    dim_ppfd = pubs["homeassistant/number/spiderfarmer_ggs_1_light_dim_threshold_ppfd/config"]

    assert dim_sched["device"]["identifiers"] == ["spiderfarmer_ggs_1_light_schedule"]
    assert dim_ppfd["device"]["identifiers"] == ["spiderfarmer_ggs_1_light_ppfd"]
    # Same wire topics so HA stays in sync
    assert dim_sched["state_topic"] == dim_ppfd["state_topic"]
    assert dim_sched["command_topic"] == dim_ppfd["command_topic"]
    # Distinct unique_ids
    assert dim_sched["unique_id"] != dim_ppfd["unique_id"]


def test_light2_does_not_get_settings_sub_devices(mocker):
    # Only Light 1 mirrors the SF App's settings screen. Light 2 stays as
    # the simple light entity to keep the dashboard uncluttered.
    client = mocker.MagicMock()
    publish_discovery_for_device(client, "ggs_1", CFG)
    topics = {call.args[0] for call in client.publish.call_args_list}

    assert not any("light2_schedule" in t or "light2_ppfd" in t for t in topics)


def test_publish_discovery_emits_fan_env_submode_dropdown(mocker):
    client = mocker.MagicMock()
    publish_discovery_for_device(client, "ggs_1", CFG)
    pubs = _publish_calls(client)

    sel = pubs["homeassistant/select/spiderfarmer_ggs_1_fan_env_submode/config"]
    assert sel["device"]["identifiers"] == ["spiderfarmer_ggs_1_fan_env"]
    assert sel["state_topic"] == "spiderfarmer/ggs_1/state/fan/env_submode"
    assert sel["command_topic"] == "spiderfarmer/ggs_1/command/fan/env_submode/set"
    assert sel["options"] == [
        "Prioritize temperature",
        "Prioritize humidity",
        "Temperature only",
        "Humidity only",
        "Temperature & humidity",
    ]


def test_fan_env_sub_device_includes_speeds_and_natural_wind(mocker):
    client = mocker.MagicMock()
    publish_discovery_for_device(client, "ggs_1", CFG)
    pubs = _publish_calls(client)

    # Min/Max speed aliased into Env card — same wire topics, distinct uids.
    speed_env = pubs["homeassistant/number/spiderfarmer_ggs_1_fan_schedule_speed_env/config"]
    speed_main = pubs["homeassistant/number/spiderfarmer_ggs_1_fan_schedule_speed/config"]
    assert speed_env["device"]["identifiers"] == ["spiderfarmer_ggs_1_fan_env"]
    assert speed_env["state_topic"] == speed_main["state_topic"]
    assert speed_env["command_topic"] == speed_main["command_topic"]
    assert speed_env["unique_id"] != speed_main["unique_id"]

    standby_env = pubs["homeassistant/number/spiderfarmer_ggs_1_fan_standby_speed_env/config"]
    assert standby_env["device"]["identifiers"] == ["spiderfarmer_ggs_1_fan_env"]

    nw_env = pubs["homeassistant/switch/spiderfarmer_ggs_1_fan_natural_wind_env/config"]
    assert nw_env["device"]["identifiers"] == ["spiderfarmer_ggs_1_fan_env"]


def test_blower_gets_full_app_parity_minus_oscillation_and_natural_wind(mocker):
    # Blower (Fan Exhaust) is the same set of cards as the Fan Circulation,
    # just with speed range 1-100 and without the oscillation_level /
    # natural_wind entities (the exhaust fan has no shaking head and no
    # natural-wind feature).
    client = mocker.MagicMock()
    publish_discovery_for_device(client, "ggs_1", CFG)
    pubs = _publish_calls(client)
    topics = set(pubs)

    # Same four sub-devices as fan
    for slug in ("schedule", "cycle", "env", "speeds"):
        assert any(f"blower_{slug}" in str(p["device"]["identifiers"])
                   for p in pubs.values()), f"missing sub-device blower_{slug}"

    # Speed entities exist with 1-100 range
    sp = pubs["homeassistant/number/spiderfarmer_ggs_1_blower_schedule_speed/config"]
    assert sp["min"] == 1 and sp["max"] == 100
    sb = pubs["homeassistant/number/spiderfarmer_ggs_1_blower_standby_speed/config"]
    assert sb["min"] == 0 and sb["max"] == 100

    # Env-mode submode dropdown
    assert "homeassistant/select/spiderfarmer_ggs_1_blower_env_submode/config" in topics

    # No oscillation_level, no natural_wind anywhere on blower
    for t in topics:
        assert "blower_oscillation_level" not in t, t
        assert "blower_natural_wind" not in t, t


def test_standby_speed_appears_in_every_fan_card(mocker):
    # Standby Speed (= controller's minSpeed) is what the fan runs at when
    # conditions are at target. It applies in every mode, so the user wants
    # it visible under each of the four cards. Same wire topics, distinct
    # unique_ids so toggling one keeps the others in sync.
    client = mocker.MagicMock()
    publish_discovery_for_device(client, "ggs_1", CFG)
    pubs = _publish_calls(client)

    main = pubs["homeassistant/number/spiderfarmer_ggs_1_fan_standby_speed/config"]
    sched = pubs["homeassistant/number/spiderfarmer_ggs_1_fan_standby_speed_schedule/config"]
    cycle = pubs["homeassistant/number/spiderfarmer_ggs_1_fan_standby_speed_cycle/config"]
    env = pubs["homeassistant/number/spiderfarmer_ggs_1_fan_standby_speed_env/config"]

    # All four point at the same wire topics
    for alias in (sched, cycle, env):
        assert alias["state_topic"] == main["state_topic"]
        assert alias["command_topic"] == main["command_topic"]
        assert alias["unique_id"] != main["unique_id"]

    # And land in the right sub-devices
    assert sched["device"]["identifiers"] == ["spiderfarmer_ggs_1_fan_schedule"]
    assert cycle["device"]["identifiers"] == ["spiderfarmer_ggs_1_fan_cycle"]
    assert env["device"]["identifiers"] == ["spiderfarmer_ggs_1_fan_env"]
    assert main["device"]["identifiers"] == ["spiderfarmer_ggs_1_fan_speeds"]


def test_natural_wind_appears_in_schedule_cycle_env_and_speeds(mocker):
    # User wants natural_wind in every fan settings card. All four entities
    # share state/command topics so toggling one updates all.
    client = mocker.MagicMock()
    publish_discovery_for_device(client, "ggs_1", CFG)
    pubs = _publish_calls(client)

    nw_speeds = pubs["homeassistant/switch/spiderfarmer_ggs_1_fan_natural_wind/config"]
    nw_sched = pubs["homeassistant/switch/spiderfarmer_ggs_1_fan_natural_wind_schedule/config"]
    nw_cycle = pubs["homeassistant/switch/spiderfarmer_ggs_1_fan_natural_wind_cycle/config"]
    nw_env = pubs["homeassistant/switch/spiderfarmer_ggs_1_fan_natural_wind_env/config"]

    # All four point at the same wire topics
    for alias in (nw_sched, nw_cycle, nw_env):
        assert alias["state_topic"] == nw_speeds["state_topic"]
        assert alias["command_topic"] == nw_speeds["command_topic"]
        assert alias["unique_id"] != nw_speeds["unique_id"]

    # And land in the right sub-devices
    assert nw_sched["device"]["identifiers"] == ["spiderfarmer_ggs_1_fan_schedule"]
    assert nw_cycle["device"]["identifiers"] == ["spiderfarmer_ggs_1_fan_cycle"]
    assert nw_env["device"]["identifiers"] == ["spiderfarmer_ggs_1_fan_env"]
    assert nw_speeds["device"]["identifiers"] == ["spiderfarmer_ggs_1_fan_speeds"]


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
