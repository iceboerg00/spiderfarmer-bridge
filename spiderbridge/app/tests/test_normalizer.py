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
    data = {"data": {"sensor": {"tempSoil": 22.0, "humiSoil": 60.0, "ECSoil": 1.5}}}
    r = normalize_status("ggs_1", data)
    assert r["spiderfarmer/ggs_1/state/temp_soil"] == "22.0"
    assert r["spiderfarmer/ggs_1/state/humi_soil"] == "60.0"
    assert r["spiderfarmer/ggs_1/state/ec_soil"] == "1.5"


def test_light_emits_json_payload_with_manual_mode():
    data = {"data": {"light": {"on": 1, "level": 80, "modeType": 1}}}
    r = normalize_status("ggs_1", data)
    p = json.loads(r["spiderfarmer/ggs_1/state/light"])
    assert p == {"state": "ON", "brightness": 80, "effect": "Modus: Manual / Timer"}


def test_light_off_state():
    data = {"data": {"light": {"on": 0, "level": 0, "modeType": 1}}}
    p = json.loads(normalize_status("ggs_1", data)["spiderfarmer/ggs_1/state/light"])
    assert p["state"] == "OFF"


def test_light2_ppfd_mode():
    data = {"data": {"light2": {"on": 1, "level": 50, "modeType": 12}}}
    p = json.loads(normalize_status("ggs_1", data)["spiderfarmer/ggs_1/state/light2"])
    assert p["effect"] == "Modus: PPFD"


def test_light_falls_back_to_mlevel_and_monoff_aliases():
    data = {"data": {"light": {"mOnOff": 1, "mLevel": 42}}}
    p = json.loads(normalize_status("ggs_1", data)["spiderfarmer/ggs_1/state/light"])
    assert p["state"] == "ON"
    assert p["brightness"] == 42


def test_blower_json_payload():
    data = {"data": {"blower": {"on": 1, "level": 75}}}
    p = json.loads(normalize_status("ggs_1", data)["spiderfarmer/ggs_1/state/blower"])
    assert p == {"state": "ON", "percentage": 75}


def test_fan_json_payload():
    data = {"data": {"fan": {"on": 0, "level": 5}}}
    p = json.loads(normalize_status("ggs_1", data)["spiderfarmer/ggs_1/state/fan"])
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
        {"id": "avg",    "tempSoil": 22.0},
    ]}}
    r = normalize_status("ggs_1", data)
    assert r["spiderfarmer/ggs_1/state/soil_ABC123_temp"] == "22.5"
    assert r["spiderfarmer/ggs_1/state/soil_ABC123_humi"] == "60.0"
    assert r["spiderfarmer/ggs_1/state/soil_ABC123_ec"] == "1.2"
    assert "spiderfarmer/ggs_1/state/soil_avg_temp" not in r


def test_accepts_unwrapped_data():
    r = normalize_status("ggs_1", {"heater": {"mOnOff": 1}})
    assert r["spiderfarmer/ggs_1/state/heater"] == "ON"


def test_on_off_value_variants():
    for on_val in (1, True, "1", "true", "on"):
        d = {"data": {"heater": {"mOnOff": on_val}}}
        assert normalize_status("ggs_1", d)["spiderfarmer/ggs_1/state/heater"] == "ON"
    for off_val in (0, False, "0", "false", "off", "OFF"):
        d = {"data": {"heater": {"mOnOff": off_val}}}
        assert normalize_status("ggs_1", d)["spiderfarmer/ggs_1/state/heater"] == "OFF"
