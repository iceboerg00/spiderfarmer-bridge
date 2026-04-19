from proxy.command_handler import translate_command


def test_blower_speed():
    r = translate_command("blower_speed", "5", "AABBCC", "uid1")
    assert r["method"] == "setConfigField"
    assert r["params"]["keyPath"] == ["device", "blower"]
    assert r["params"]["blower"]["mLevel"] == 5


def test_fan_speed():
    r = translate_command("fan_speed", "7", "AABBCC", "uid1")
    assert r["params"]["keyPath"] == ["device", "fan"]
    assert r["params"]["fan"]["mLevel"] == 7


def test_light_1_brightness():
    r = translate_command("light_1_brightness", "80", "AABBCC", "uid1")
    assert r["params"]["keyPath"] == ["device", "light"]
    assert r["params"]["light"]["mLevel"] == 80


def test_light_2_brightness():
    r = translate_command("light_2_brightness", "50", "AABBCC", "uid1")
    assert r["params"]["keyPath"] == ["device", "light2"]
    assert r["params"]["light2"]["mLevel"] == 50


def test_heater_on():
    r = translate_command("heater", "ON", "AABBCC", "uid1")
    assert r["params"]["heater"]["mOnOff"] == 1


def test_heater_off():
    r = translate_command("heater", "OFF", "AABBCC", "uid1")
    assert r["params"]["heater"]["mOnOff"] == 0


def test_humidifier_on():
    r = translate_command("humidifier", "ON", "AABBCC", "uid1")
    assert r["params"]["humidifier"]["mOnOff"] == 1


def test_dehumidifier_off():
    r = translate_command("dehumidifier", "OFF", "AABBCC", "uid1")
    assert r["params"]["dehumidifier"]["mOnOff"] == 0


def test_outlet_on():
    r = translate_command("outlet_3", "ON", "AABBCC", "uid1", outlet_num=3)
    assert r["params"]["keyPath"] == ["outlet", "O3"]
    assert r["params"]["O3"]["mOnOff"] == 1


def test_outlet_off():
    r = translate_command("outlet_1", "OFF", "AABBCC", "uid1", outlet_num=1)
    assert r["params"]["O1"]["mOnOff"] == 0


def test_out_of_range_blower():
    r = translate_command("blower_speed", "99", "AABBCC", "uid1")
    assert r is None


def test_out_of_range_negative():
    r = translate_command("fan_speed", "-1", "AABBCC", "uid1")
    assert r is None


def test_unknown_field():
    r = translate_command("unknown_field", "1", "AABBCC", "uid1")
    assert r is None


def test_invalid_value_type():
    r = translate_command("blower_speed", "notanumber", "AABBCC", "uid1")
    assert r is None


def test_includes_mac_uid_timestamps():
    r = translate_command("fan_speed", "3", "AABBCC", "uid1")
    assert r["pid"] == "AABBCC"
    assert r["uid"] == "uid1"
    assert isinstance(r["msgId"], int)
    assert isinstance(r["UTC"], int)
