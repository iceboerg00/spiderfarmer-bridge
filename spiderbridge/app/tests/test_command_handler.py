import json

from proxy.command_handler import translate_command


# ── Outlets ──────────────────────────────────────────────────────────────────

def test_outlet_on():
    r = translate_command("outlet_3", "ON", "AABBCC", "uid1", outlet_num=3)
    assert r["method"] == "setConfigField"
    assert r["pid"] == "AABBCC"
    assert r["uid"] == "uid1"
    assert r["params"]["keyPath"] == ["outlet", "O3"]
    assert r["params"]["O3"]["mOnOff"] == 1


def test_outlet_off():
    r = translate_command("outlet_1", "OFF", "AABBCC", "uid1", outlet_num=1)
    assert r["params"]["O1"]["mOnOff"] == 0


# ── Light / Light2 ──────────────────────────────────────────────────────────

def test_light_full_json_payload_with_ppfd_mode():
    val = json.dumps({"state": "ON", "brightness": 80, "effect": "Modus: PPFD"})
    r = translate_command("light", val, "AABBCC", "uid1")
    assert r["params"]["keyPath"] == ["device", "light"]
    assert r["params"]["light"]["mOnOff"] == 1
    assert r["params"]["light"]["mLevel"] == 80
    assert r["params"]["light"]["modeType"] == 12


def test_light2_full_json_payload_with_manual_mode():
    val = json.dumps({"state": "ON", "brightness": 50, "effect": "Modus: Manual / Timer"})
    r = translate_command("light2", val, "AABBCC", "uid1")
    assert r["params"]["keyPath"] == ["device", "light2"]
    assert r["params"]["light2"]["modeType"] == 1


def test_light_brightness_clamped_high():
    r = translate_command("light", json.dumps({"state": "ON", "brightness": 999}), "AABBCC", "uid1")
    assert r["params"]["light"]["mLevel"] == 100


def test_light_brightness_clamped_low():
    r = translate_command("light", json.dumps({"state": "ON", "brightness": -10}), "AABBCC", "uid1")
    assert r["params"]["light"]["mLevel"] == 0


def test_light_uses_device_state_when_brightness_omitted():
    val = json.dumps({"state": "ON"})
    state = {"light": {"level": 42, "modeType": 1}}
    r = translate_command("light", val, "AABBCC", "uid1", device_state=state)
    assert r["params"]["light"]["mLevel"] == 42


def test_light_off_with_plain_string_value():
    r = translate_command("light", "OFF", "AABBCC", "uid1")
    assert r["params"]["light"]["mOnOff"] == 0


# ── Blower (exhaust fan) ─────────────────────────────────────────────────────

def test_blower_on_off_no_subfield():
    on = translate_command("blower", "ON", "AABBCC", "uid1")
    assert on["params"]["keyPath"] == ["device", "blower"]
    assert on["params"]["blower"]["mOnOff"] == 1
    off = translate_command("blower", "OFF", "AABBCC", "uid1")
    assert off["params"]["blower"]["mOnOff"] == 0


def test_blower_percentage_subfield():
    r = translate_command("blower", "75", "AABBCC", "uid1", subfield="percentage")
    assert r["params"]["blower"]["mLevel"] == 75


def test_blower_percentage_clamped_min_is_1():
    r = translate_command("blower", "0", "AABBCC", "uid1", subfield="percentage")
    assert r["params"]["blower"]["mLevel"] == 1


def test_blower_percentage_clamped_max_is_100():
    r = translate_command("blower", "200", "AABBCC", "uid1", subfield="percentage")
    assert r["params"]["blower"]["mLevel"] == 100


def test_blower_percentage_invalid_returns_none():
    r = translate_command("blower", "abc", "AABBCC", "uid1", subfield="percentage")
    assert r is None


# ── Fan (circulation, speed 1–10) ────────────────────────────────────────────

def test_fan_on_off_no_subfield():
    r = translate_command("fan", "OFF", "AABBCC", "uid1")
    assert r["params"]["fan"]["mOnOff"] == 0


def test_fan_percentage_subfield():
    r = translate_command("fan", "5", "AABBCC", "uid1", subfield="percentage")
    assert r["params"]["fan"]["mLevel"] == 5


def test_fan_percentage_clamped_to_10():
    r = translate_command("fan", "99", "AABBCC", "uid1", subfield="percentage")
    assert r["params"]["fan"]["mLevel"] == 10


# ── Climate accessories ──────────────────────────────────────────────────────

def test_heater_on_off():
    on = translate_command("heater", "ON", "AABBCC", "uid1")
    assert on["params"]["heater"]["mOnOff"] == 1
    off = translate_command("heater", "OFF", "AABBCC", "uid1")
    assert off["params"]["heater"]["mOnOff"] == 0


def test_humidifier_on():
    r = translate_command("humidifier", "ON", "AABBCC", "uid1")
    assert r["params"]["humidifier"]["mOnOff"] == 1


def test_dehumidifier_off():
    r = translate_command("dehumidifier", "OFF", "AABBCC", "uid1")
    assert r["params"]["dehumidifier"]["mOnOff"] == 0


# ── Generic ──────────────────────────────────────────────────────────────────

def test_unknown_field_returns_none():
    assert translate_command("not_a_field", "ON", "AABBCC", "uid1") is None


def test_payload_includes_pid_uid_and_msg_id():
    r = translate_command("heater", "ON", "AABBCC", "uid1")
    assert r["pid"] == "AABBCC"
    assert r["uid"] == "uid1"
    assert isinstance(r["msgId"], str)
    assert int(r["msgId"]) > 0
