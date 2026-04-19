from proxy.normalizer import normalize_sensors, normalize_status


def test_sensors_all_fields():
    data = {"temp": 24.5, "humi": 65.2, "vpd": 1.1, "co2": 800, "ppfd": 600}
    result = normalize_sensors("ggs_1", data)
    assert result["spiderfarmer/ggs_1/state/temperature"] == "24.5"
    assert result["spiderfarmer/ggs_1/state/humidity"] == "65.2"
    assert result["spiderfarmer/ggs_1/state/vpd"] == "1.1"
    assert result["spiderfarmer/ggs_1/state/co2"] == "800"
    assert result["spiderfarmer/ggs_1/state/ppfd"] == "600"


def test_sensors_partial_fields():
    result = normalize_sensors("ggs_1", {"temp": 22.0})
    assert "spiderfarmer/ggs_1/state/temperature" in result
    assert "spiderfarmer/ggs_1/state/humidity" not in result


def test_sensors_ignores_unknown_fields():
    result = normalize_sensors("ggs_1", {"temp": 20.0, "uid": "abc", "junk": 99})
    assert len(result) == 1


def test_status_blower_mlevel():
    data = {"data": {"blower": {"mLevel": 5}}}
    result = normalize_status("ggs_1", data)
    assert result["spiderfarmer/ggs_1/state/blower_speed"] == "5"


def test_status_blower_level_alias():
    # Some firmware uses 'level' instead of 'mLevel'
    data = {"data": {"blower": {"level": 3}}}
    result = normalize_status("ggs_1", data)
    assert result["spiderfarmer/ggs_1/state/blower_speed"] == "3"


def test_status_heater_on():
    data = {"data": {"heater": {"mOnOff": 1}}}
    result = normalize_status("ggs_1", data)
    assert result["spiderfarmer/ggs_1/state/heater"] == "ON"


def test_status_heater_off():
    data = {"data": {"heater": {"mOnOff": 0}}}
    result = normalize_status("ggs_1", data)
    assert result["spiderfarmer/ggs_1/state/heater"] == "OFF"


def test_status_outlets():
    data = {"data": {"outlet": {"O1": {"mOnOff": 1}, "O3": {"mOnOff": 0}}}}
    result = normalize_status("ggs_1", data)
    assert result["spiderfarmer/ggs_1/state/outlet_1"] == "ON"
    assert result["spiderfarmer/ggs_1/state/outlet_3"] == "OFF"


def test_status_sensor_block():
    data = {"data": {"sensor": {"temp": 23.0, "humi": 70.0}}}
    result = normalize_status("ggs_1", data)
    assert result["spiderfarmer/ggs_1/state/temperature"] == "23.0"
    assert result["spiderfarmer/ggs_1/state/humidity"] == "70.0"


def test_status_light_levels():
    data = {"data": {"light": {"mLevel": 80}, "light2": {"mLevel": 50}}}
    result = normalize_status("ggs_1", data)
    assert result["spiderfarmer/ggs_1/state/light_1_brightness"] == "80"
    assert result["spiderfarmer/ggs_1/state/light_2_brightness"] == "50"


def test_status_fan_and_humidifier():
    data = {"data": {"fan": {"mLevel": 7}, "humidifier": {"mOnOff": 1}, "dehumidifier": {"mOnOff": 0}}}
    result = normalize_status("ggs_1", data)
    assert result["spiderfarmer/ggs_1/state/fan_speed"] == "7"
    assert result["spiderfarmer/ggs_1/state/humidifier"] == "ON"
    assert result["spiderfarmer/ggs_1/state/dehumidifier"] == "OFF"


def test_status_unwrapped_data():
    # Some messages may not have a 'data' wrapper
    data = {"blower": {"mLevel": 4}}
    result = normalize_status("ggs_1", data)
    assert result["spiderfarmer/ggs_1/state/blower_speed"] == "4"


def test_status_on_off_string_and_bool_variants():
    """_on_off handles all documented variants: 1, True, '1', 'true', 'on' → ON; rest → OFF."""
    for on_val in (1, True, "1", "true", "on"):
        data = {"data": {"heater": {"mOnOff": on_val}}}
        result = normalize_status("ggs_1", data)
        assert result["spiderfarmer/ggs_1/state/heater"] == "ON", f"Expected ON for mOnOff={on_val!r}"
    for off_val in (0, False, "0", "false", "off", "OFF"):
        data = {"data": {"heater": {"mOnOff": off_val}}}
        result = normalize_status("ggs_1", data)
        assert result["spiderfarmer/ggs_1/state/heater"] == "OFF", f"Expected OFF for mOnOff={off_val!r}"
