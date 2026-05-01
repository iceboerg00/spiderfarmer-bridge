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
    assert r["params"]["keyPath"] == ["outlet", "O1"]
    assert r["params"]["O1"]["mOnOff"] == 0


def test_outlet_sends_full_default_block_for_ps5_ps10_compatibility():
    # PS5/PS10 ignore minimal {modeType, mOnOff} commands and need the full
    # outlet block. The shape mirrors a real SF App capture for a simple
    # (non-watering) outlet: cycleTime only carries weekmask, timePeriod has
    # exactly 9 entries (4 default-active, 5 disabled), tempAdd/humiAdd are
    # present even when zero. Sending this authoritatively overwrites any
    # user-configured cycle/schedule from the SF App, which is intended.
    r = translate_command("outlet_3", "ON", "AABBCC", "uid1", outlet_num=3)
    out = r["params"]["O3"]
    assert out["mOnOff"] == 1
    assert out["modeType"] == 0
    assert out["cycleTime"] == {"weekmask": 127}
    assert len(out["timePeriod"]) == 9
    assert out["timePeriod"][0] == {"weekmask": 127}
    assert out["timePeriod"][4] == {"enabled": 0, "weekmask": 127}
    assert out["tempAdd"] == 0
    assert out["humiAdd"] == 0


# ── Light / Light2 ──────────────────────────────────────────────────────────

def test_light_full_json_payload_with_ppfd_mode():
    val = json.dumps({"state": "ON", "brightness": 80, "effect": "Modus: PPFD"})
    r = translate_command("light", val, "AABBCC", "uid1")
    assert r["params"]["keyPath"] == ["device", "light"]
    assert r["params"]["light"]["mOnOff"] == 1
    assert r["params"]["light"]["mLevel"] == 80
    assert r["params"]["light"]["modeType"] == 12  # PPFD


def test_light2_full_json_payload_with_manual_mode():
    # "Modus: Manual / Timer" effect maps to modeType 0 (Manual). Sending
    # modeType 1 (Timer) makes the controller follow the schedule and ignore
    # direct mOnOff/mLevel commands, which broke HA control of the lamp.
    val = json.dumps({"state": "ON", "brightness": 50, "effect": "Modus: Manual / Timer"})
    r = translate_command("light2", val, "AABBCC", "uid1")
    assert r["params"]["keyPath"] == ["device", "light2"]
    assert r["params"]["light2"]["modeType"] == 0
    assert r["params"]["light2"]["mLevel"] == 50


def test_light_default_mode_is_manual():
    # ON without explicit effect defaults to modeType 0 (Manual) — never
    # Timer (1), even if the controller currently reports Timer.
    val = json.dumps({"state": "ON", "brightness": 60})
    cur = {"light": {"modeType": 1, "level": 60}}
    r = translate_command("light", val, "AABBCC", "uid1", device_state=cur)
    assert r["params"]["light"]["modeType"] == 0


def test_light_payload_includes_last_auto_mode_type():
    val = json.dumps({"state": "ON", "brightness": 50})
    cur = {"light": {"lastAutoModeType": 12}}
    r = translate_command("light", val, "AABBCC", "uid1", device_state=cur)
    assert r["params"]["light"]["lastAutoModeType"] == 12


def test_light_payload_preserves_existing_time_period():
    # Use the controller's stored schedule rather than wiping it with the
    # minimal placeholder.
    sched = [{"enabled": 1, "weekmask": 127, "startTime": 21600,
              "endTime": 0, "brightness": 40, "fadeTime": 900}]
    val = json.dumps({"state": "ON", "brightness": 50})
    cur = {"light": {"timePeriod": sched}}
    r = translate_command("light", val, "AABBCC", "uid1", device_state=cur)
    assert r["params"]["light"]["timePeriod"] == sched


def test_light_falls_back_to_minimal_time_period_when_unknown():
    val = json.dumps({"state": "ON", "brightness": 50})
    r = translate_command("light", val, "AABBCC", "uid1")
    assert r["params"]["light"]["timePeriod"] == [{"weekmask": 127}]


def test_light_brightness_clamped_high():
    val = json.dumps({"state": "ON", "brightness": 999})
    r = translate_command("light", val, "AABBCC", "uid1")
    assert r["params"]["light"]["mLevel"] == 100


def test_light_brightness_clamped_low():
    val = json.dumps({"state": "ON", "brightness": -10})
    r = translate_command("light", val, "AABBCC", "uid1")
    assert r["params"]["light"]["mLevel"] == 0


def test_light_uses_device_state_when_brightness_omitted():
    val = json.dumps({"state": "ON"})
    state = {"light": {"level": 42, "modeType": 1}}
    r = translate_command("light", val, "AABBCC", "uid1", device_state=state)
    assert r["params"]["light"]["mLevel"] == 42


def test_light_off_with_plain_string_value():
    # When HA sends a non-JSON value, it is treated as state alone
    r = translate_command("light", "OFF", "AABBCC", "uid1")
    assert r["params"]["light"]["mOnOff"] == 0


def test_light_on_after_off_restores_last_nonzero_brightness():
    # Symptom: HA sends {"state":"ON"} (no brightness) right after turning the
    # light off. Device state at that moment reports level=0 (light is off), so
    # the old fallback chain produced mLevel=0 — light "on" but invisible.
    # Fix: when on=1 and resolved level=0, fall back to last non-zero level.
    val = json.dumps({"state": "ON"})
    cur_state = {"light": {"level": 0, "modeType": 1}}
    last = {"light": 40}
    r = translate_command("light", val, "AABBCC", "uid1",
                          device_state=cur_state, last_nonzero_level=last)
    assert r["params"]["light"]["mOnOff"] == 1
    assert r["params"]["light"]["mLevel"] == 40


def test_light_on_no_history_defaults_to_full():
    # First ever ON with no last_nonzero_level history and current level 0 →
    # default to 100 % so the light is at least visible.
    val = json.dumps({"state": "ON"})
    cur_state = {"light": {"level": 0, "modeType": 1}}
    r = translate_command("light", val, "AABBCC", "uid1",
                          device_state=cur_state, last_nonzero_level={})
    assert r["params"]["light"]["mOnOff"] == 1
    assert r["params"]["light"]["mLevel"] == 100


def test_light_explicit_brightness_overrides_last_level():
    # Explicit brightness from HA always wins, regardless of last_nonzero_level.
    val = json.dumps({"state": "ON", "brightness": 25})
    last = {"light": 80}
    r = translate_command("light", val, "AABBCC", "uid1", last_nonzero_level=last)
    assert r["params"]["light"]["mLevel"] == 25


def test_light2_on_after_off_restores_last_nonzero_brightness():
    val = json.dumps({"state": "ON"})
    cur_state = {"light2": {"level": 0, "modeType": 1}}
    last = {"light2": 75}
    r = translate_command("light2", val, "AABBCC", "uid1",
                          device_state=cur_state, last_nonzero_level=last)
    assert r["params"]["light2"]["mLevel"] == 75


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
    # The implementation clamps to [1, 100], not [0, 100]
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
    assert r["params"]["keyPath"] == ["device", "fan"]
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
    assert on["params"]["keyPath"] == ["device", "heater"]
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
    r = translate_command("not_a_field", "ON", "AABBCC", "uid1")
    assert r is None


def test_payload_includes_pid_uid_and_msg_id():
    r = translate_command("heater", "ON", "AABBCC", "uid1")
    assert r["pid"] == "AABBCC"
    assert r["uid"] == "uid1"
    # msgId is a string of millisecond timestamp
    assert isinstance(r["msgId"], str)
    assert int(r["msgId"]) > 0
