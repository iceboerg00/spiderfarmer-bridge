import json

from proxy.normalizer import normalize_status


def test_air_sensors_all_fields():
    data = {"data": {"sensor": {
        "temp": 24.5, "humi": 65.2, "vpd": 1.1, "co2": 800, "ppfd": 600,
    }}}
    r = normalize_status("ggs_1", data)
    assert r["spiderfarmer/ggs_1/state/temperature"] == "24.5"
    assert r["spiderfarmer/ggs_1/state/humidity"] == "65.2"
    assert r["spiderfarmer/ggs_1/state/vpd"] == "1.1"
    assert r["spiderfarmer/ggs_1/state/co2"] == "800"
    assert r["spiderfarmer/ggs_1/state/ppfd"] == "600"


def test_air_sensors_partial():
    r = normalize_status("ggs_1", {"data": {"sensor": {"temp": 22.0}}})
    assert "spiderfarmer/ggs_1/state/temperature" in r
    assert "spiderfarmer/ggs_1/state/humidity" not in r


def test_soil_avg_block_emits_top_level_topics():
    # tempSoil/humiSoil/ECSoil at sensor-block top level → soil_avg topics
    data = {"data": {"sensor": {"tempSoil": 22.0, "humiSoil": 60.0, "ECSoil": 1.5}}}
    r = normalize_status("ggs_1", data)
    assert r["spiderfarmer/ggs_1/state/temp_soil"] == "22.0"
    assert r["spiderfarmer/ggs_1/state/humi_soil"] == "60.0"
    assert r["spiderfarmer/ggs_1/state/ec_soil"] == "1.5"


def test_light_emits_json_payload_with_schedule_mode():
    data = {"data": {"light": {"on": 1, "level": 80, "modeType": 1}}}
    r = normalize_status("ggs_1", data)
    p = json.loads(r["spiderfarmer/ggs_1/state/light"])
    assert p == {"state": "ON", "brightness": 80, "effect": "Schedule"}


def test_light_mode_zero_displays_as_manual():
    # modeType 0 = "Manueller Modus" per SF App; modeType 1 is a different
    # mode (Schedule / Zeitfenster). They must surface as distinct effects
    # in HA so the dropdown reflects what the controller is actually doing.
    data = {"data": {"light": {"on": 1, "level": 80, "modeType": 0}}}
    r = normalize_status("ggs_1", data)
    p = json.loads(r["spiderfarmer/ggs_1/state/light"])
    assert p["effect"] == "Manual"


def test_light_off_state():
    data = {"data": {"light": {"on": 0, "level": 0, "modeType": 1}}}
    r = normalize_status("ggs_1", data)
    p = json.loads(r["spiderfarmer/ggs_1/state/light"])
    assert p["state"] == "OFF"


def test_light2_ppfd_mode():
    data = {"data": {"light2": {"on": 1, "level": 50, "modeType": 12}}}
    r = normalize_status("ggs_1", data)
    p = json.loads(r["spiderfarmer/ggs_1/state/light2"])
    assert p["effect"] == "PPFD"


def test_light_controller_flat_schema_maps_to_light_topic():
    # Standalone Light Controller (LC) reports brightness/mode flat under
    # data, not nested under data.light. Map it to the same `state/light`
    # topic so HA's light entity works without a separate code path.
    data = {"data": {"brightness": 42, "mode": 12}}
    r = normalize_status("ggs_1", data)
    p = json.loads(r["spiderfarmer/ggs_1/state/light"])
    assert p["state"] == "ON"
    assert p["brightness"] == 42
    assert p["effect"] == "PPFD"


def test_light_controller_flat_schema_off_when_brightness_zero():
    data = {"data": {"brightness": 0, "mode": 0}}
    r = normalize_status("ggs_1", data)
    p = json.loads(r["spiderfarmer/ggs_1/state/light"])
    assert p["state"] == "OFF"
    assert p["brightness"] == 0


def test_nested_light_takes_precedence_over_flat_lc_schema():
    # If both shapes appear (CB+LC mixed setup or mock), the nested
    # `data.light` wins so existing CB setups are not broken.
    data = {
        "data": {
            "brightness": 99,
            "mode": 12,
            "light": {"on": 1, "level": 50, "modeType": 0},
        }
    }
    r = normalize_status("ggs_1", data)
    p = json.loads(r["spiderfarmer/ggs_1/state/light"])
    assert p["brightness"] == 50
    assert p["effect"] == "Manual"


def test_light_falls_back_to_mlevel_and_monoff_aliases():
    # Some firmware uses mLevel/mOnOff instead of level/on
    data = {"data": {"light": {"mOnOff": 1, "mLevel": 42}}}
    r = normalize_status("ggs_1", data)
    p = json.loads(r["spiderfarmer/ggs_1/state/light"])
    assert p["state"] == "ON"
    assert p["brightness"] == 42


def test_blower_json_payload():
    data = {"data": {"blower": {"on": 1, "level": 75}}}
    r = normalize_status("ggs_1", data)
    p = json.loads(r["spiderfarmer/ggs_1/state/blower"])
    assert p == {"state": "ON", "percentage": 75}


def test_fan_json_payload():
    data = {"data": {"fan": {"on": 0, "level": 5}}}
    r = normalize_status("ggs_1", data)
    p = json.loads(r["spiderfarmer/ggs_1/state/fan"])
    assert p == {"state": "OFF", "percentage": 5}


def test_heater_humidifier_dehumidifier():
    data = {"data": {
        "heater":       {"mOnOff": 1},
        "humidifier":   {"mOnOff": 0},
        "dehumidifier": {"mOnOff": 1},
    }}
    r = normalize_status("ggs_1", data)
    assert r["spiderfarmer/ggs_1/state/heater"] == "ON"
    assert r["spiderfarmer/ggs_1/state/humidifier"] == "OFF"
    assert r["spiderfarmer/ggs_1/state/dehumidifier"] == "ON"


def test_outlets_emit_per_socket_topics():
    data = {"data": {"outlet": {
        "O1": {"mOnOff": 1},
        "O3": {"mOnOff": 0},
        "O7": {"mOnOff": 1},
    }}}
    r = normalize_status("ggs_1", data)
    assert r["spiderfarmer/ggs_1/state/outlet_1"] == "ON"
    assert r["spiderfarmer/ggs_1/state/outlet_3"] == "OFF"
    assert r["spiderfarmer/ggs_1/state/outlet_7"] == "ON"


def test_individual_soil_sensors_emit_per_id_topics():
    data = {"data": {"sensors": [
        {"id": "ABC123", "tempSoil": 22.5, "humiSoil": 60.0, "ECSoil": 1.2},
        {"id": "avg",    "tempSoil": 22.0},  # avg has no per-sensor topic
    ]}}
    r = normalize_status("ggs_1", data)
    assert r["spiderfarmer/ggs_1/state/soil_ABC123_temp"] == "22.5"
    assert r["spiderfarmer/ggs_1/state/soil_ABC123_humi"] == "60.0"
    assert r["spiderfarmer/ggs_1/state/soil_ABC123_ec"] == "1.2"
    assert "spiderfarmer/ggs_1/state/soil_avg_temp" not in r


def test_accepts_unwrapped_data():
    # Some payloads may not have a 'data' wrapper
    r = normalize_status("ggs_1", {"heater": {"mOnOff": 1}})
    assert r["spiderfarmer/ggs_1/state/heater"] == "ON"


def test_on_off_value_variants():
    for on_val in (1, True, "1", "true", "on"):
        d = {"data": {"heater": {"mOnOff": on_val}}}
        assert normalize_status("ggs_1", d)["spiderfarmer/ggs_1/state/heater"] == "ON"
    for off_val in (0, False, "0", "false", "off", "OFF"):
        d = {"data": {"heater": {"mOnOff": off_val}}}
        assert normalize_status("ggs_1", d)["spiderfarmer/ggs_1/state/heater"] == "OFF"


# ── Fan app-parity (extra fields) ───────────────────────────────────────────

def test_fan_emits_mode_label_and_schedule_extras():
    data = {"data": {"fan": {
        "modeType": 1, "mOnOff": 1, "mLevel": 3,
        "shakeLevel": 6, "natural": 1,
        "minSpeed": 2, "maxSpeed": 5,
        "timePeriod": [{"enabled": 1, "weekmask": 127,
                        "startTime": 21600, "endTime": 72000}],
        "cycleTime": {"weekmask": 127},
    }}}
    r = normalize_status("ggs_1", data)
    assert r["spiderfarmer/ggs_1/state/fan/mode_label"] == "Schedule"
    assert r["spiderfarmer/ggs_1/state/fan/schedule_speed"] == "5"
    assert r["spiderfarmer/ggs_1/state/fan/standby_speed"] == "2"
    assert r["spiderfarmer/ggs_1/state/fan/oscillation_level"] == "6"
    assert r["spiderfarmer/ggs_1/state/fan/natural_wind"] == "ON"
    assert r["spiderfarmer/ggs_1/state/fan/schedule_start"] == "06:00"
    assert r["spiderfarmer/ggs_1/state/fan/schedule_end"] == "20:00"


def test_fan_emits_cycle_extras():
    data = {"data": {"fan": {
        "modeType": 2, "mOnOff": 1,
        "cycleTime": {"weekmask": 127, "startTime": 10800,
                      "openDur": 600, "closeDur": 1200, "times": 5},
    }}}
    r = normalize_status("ggs_1", data)
    assert r["spiderfarmer/ggs_1/state/fan/mode_label"] == "Cycle"
    assert r["spiderfarmer/ggs_1/state/fan/cycle_start"] == "03:00"
    assert r["spiderfarmer/ggs_1/state/fan/cycle_run_minutes"] == "10"
    assert r["spiderfarmer/ggs_1/state/fan/cycle_off_minutes"] == "20"
    assert r["spiderfarmer/ggs_1/state/fan/cycle_times"] == "5"


def test_fan_environment_modetypes_map_to_labels():
    for mt, expected in [(7, "Environment: Prioritize temperature"),
                         (8, "Environment: Prioritize humidity"),
                         (3, "Environment: Temperature only"),
                         (4, "Environment: Humidity only"),
                         (13, "Environment: Temperature & humidity")]:
        data = {"data": {"fan": {"modeType": mt}}}
        r = normalize_status("ggs_1", data)
        assert r["spiderfarmer/ggs_1/state/fan/mode_label"] == expected


def test_blower_also_gets_extras():
    data = {"data": {"blower": {
        "modeType": 1, "maxSpeed": 50, "minSpeed": 25,
    }}}
    r = normalize_status("ggs_1", data)
    assert r["spiderfarmer/ggs_1/state/blower/mode_label"] == "Schedule"
    assert r["spiderfarmer/ggs_1/state/blower/schedule_speed"] == "50"


def test_fan_env_submode_maps_only_env_modetypes():
    # Env-mode select dropdown sources from a separate state topic that
    # carries the env-only label (no "Environment: " prefix). Non-env
    # modeTypes publish "" so HA shows the dropdown as unknown.
    for mt, expected in [(7, "Prioritize temperature"),
                         (8, "Prioritize humidity"),
                         (3, "Temperature only"),
                         (4, "Humidity only"),
                         (13, "Temperature & humidity")]:
        r = normalize_status("ggs_1", {"data": {"fan": {"modeType": mt}}})
        assert r["spiderfarmer/ggs_1/state/fan/env_submode"] == expected


def test_fan_env_submode_empty_when_not_in_env_mode():
    for mt in (0, 1, 2):
        r = normalize_status("ggs_1", {"data": {"fan": {"modeType": mt}}})
        assert r["spiderfarmer/ggs_1/state/fan/env_submode"] == ""
