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


# ── Light / Light2 ──────────────────────────────────────────────────────────

def test_light_full_json_payload_with_ppfd_mode():
    val = json.dumps({"state": "ON", "brightness": 80, "effect": "PPFD"})
    r = translate_command("light", val, "AABBCC", "uid1")
    assert r["params"]["keyPath"] == ["device", "light"]
    assert r["params"]["light"]["mOnOff"] == 1
    assert r["params"]["light"]["mLevel"] == 80
    assert r["params"]["light"]["modeType"] == 12  # PPFD


def test_light2_full_json_payload_with_manual_mode():
    val = json.dumps({"state": "ON", "brightness": 50, "effect": "Manual"})
    r = translate_command("light2", val, "AABBCC", "uid1")
    assert r["params"]["keyPath"] == ["device", "light2"]
    assert r["params"]["light2"]["modeType"] == 0
    assert r["params"]["light2"]["mLevel"] == 50


def test_light_schedule_mode_maps_to_modeType_1():
    # "Schedule" effect must produce modeType=1 (Zeitfenstermodus); older
    # code merged 0 and 1 under one label which made schedule-mode
    # selection a no-op.
    val = json.dumps({"state": "ON", "brightness": 70, "effect": "Schedule"})
    r = translate_command("light", val, "AABBCC", "uid1")
    assert r["params"]["light"]["modeType"] == 1


def test_light_legacy_effect_label_still_resolves_to_manual():
    # Old HA configs that have "Modus: Manual / Timer" stored as the effect
    # should still work after the rename — the alias keeps them on
    # modeType=0 instead of falling through to the default.
    val = json.dumps({"state": "ON", "effect": "Modus: Manual / Timer"})
    r = translate_command("light", val, "AABBCC", "uid1")
    assert r["params"]["light"]["modeType"] == 0


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


# ── Fan app-parity (preset_mode + subfield writes) ──────────────────────────

def test_fan_preset_mode_maps_label_to_modeType():
    cached = {"fan": {"modeType": 0, "mOnOff": 1, "mLevel": 3,
                      "shakeLevel": 0, "natural": 0,
                      "timePeriod": [{"weekmask": 127}],
                      "cycleTime": {"weekmask": 127}}}
    r = translate_command("fan", "Environment: Prioritize temperature",
                          "AABBCC", "uid1",
                          subfield="preset_mode", fan_state=cached)
    assert r["params"]["fan"]["modeType"] == 7
    # other fields preserved
    assert r["params"]["fan"]["mLevel"] == 3
    assert r["params"]["fan"]["shakeLevel"] == 0


def test_fan_preset_mode_unknown_label_returns_none():
    r = translate_command("fan", "Bogus Mode", "AABBCC", "uid1",
                          subfield="preset_mode", fan_state={})
    assert r is None


def test_fan_env_submode_maps_label_to_modeType():
    for label, expected_mt in [("Prioritize temperature", 7),
                               ("Prioritize humidity", 8),
                               ("Temperature only", 3),
                               ("Humidity only", 4),
                               ("Temperature & humidity", 13)]:
        r = translate_command("fan", label, "AABBCC", "uid1",
                              subfield="env_submode", fan_state={})
        assert r["params"]["fan"]["modeType"] == expected_mt


def test_fan_env_submode_unknown_returns_none():
    r = translate_command("fan", "Bogus", "AABBCC", "uid1",
                          subfield="env_submode", fan_state={})
    assert r is None


def test_fan_schedule_start_parses_hhmm():
    r = translate_command("fan", "07:30", "AABBCC", "uid1",
                          subfield="schedule_start", fan_state={})
    assert r["params"]["fan"]["timePeriod"][0]["startTime"] == 7 * 3600 + 30 * 60


def test_fan_cycle_run_minutes_to_seconds():
    r = translate_command("fan", "10", "AABBCC", "uid1",
                          subfield="cycle_run_minutes", fan_state={})
    assert r["params"]["fan"]["cycleTime"]["openDur"] == 600


def test_fan_cycle_times_clamped_to_100():
    r = translate_command("fan", "9999", "AABBCC", "uid1",
                          subfield="cycle_times", fan_state={})
    assert r["params"]["fan"]["cycleTime"]["times"] == 100


def test_fan_schedule_speed_clamped_to_10():
    r = translate_command("fan", "15", "AABBCC", "uid1",
                          subfield="schedule_speed", fan_state={})
    assert r["params"]["fan"]["maxSpeed"] == 10


def test_fan_schedule_speed_also_writes_mlevel_for_manual_mode():
    # Manual mode reads mLevel, Schedule/Cycle/Env modes read maxSpeed.
    # The single HA "Speed" entity must change the fan regardless of
    # which mode is currently active, so we set both.
    r = translate_command("fan", "5", "AABBCC", "uid1",
                          subfield="schedule_speed", fan_state={})
    assert r["params"]["fan"]["maxSpeed"] == 5
    assert r["params"]["fan"]["mLevel"] == 5


def test_fan_standby_speed_zero_means_aus():
    r = translate_command("fan", "0", "AABBCC", "uid1",
                          subfield="standby_speed", fan_state={})
    assert r["params"]["fan"]["minSpeed"] == 0


def test_fan_oscillation_level_writes_shake_level():
    r = translate_command("fan", "7", "AABBCC", "uid1",
                          subfield="oscillation_level", fan_state={})
    assert r["params"]["fan"]["shakeLevel"] == 7


def test_fan_natural_wind_on_off():
    on = translate_command("fan", "ON", "AABBCC", "uid1",
                           subfield="natural_wind", fan_state={})
    off = translate_command("fan", "OFF", "AABBCC", "uid1",
                            subfield="natural_wind", fan_state={})
    assert on["params"]["fan"]["natural"] == 1
    assert off["params"]["fan"]["natural"] == 0


def test_fan_subfield_targets_blower_keypath_when_field_is_blower():
    r = translate_command("blower", "5", "AABBCC", "uid1",
                          subfield="schedule_speed", fan_state={})
    assert r["params"]["keyPath"] == ["device", "blower"]
    assert "blower" in r["params"]
    assert r["params"]["blower"]["maxSpeed"] == 5


# ── Light app-parity (subfield writes) ─────────────────────────────────────

def _light_block(**overrides):
    """Realistic cached light block as observed from cloud setConfigField."""
    blk = {
        "modeType": 1, "lastAutoModeType": 0, "mOnOff": 1, "mLevel": 65,
        "darkTemp": 0, "offTemp": 0,
        "timePeriod": [{"enabled": 1, "weekmask": 127,
                        "startTime": 21600, "endTime": 72000,
                        "brightness": 65, "fadeTime": 900}],
        "ppfdPeriod": [{"enabled": 0, "weekmask": 127,
                        "startTime": 0, "endTime": 0,
                        "brightness": 20, "fadeTime": 0}],
        "ppfdMinBrightness": 0, "ppfdMaxBrightness": 100,
    }
    blk.update(overrides)
    return {"light": blk}


def test_light_schedule_brightness_subfield():
    cached = _light_block()
    r = translate_command("light", "80", "AABBCC", "uid1",
                          subfield="schedule_brightness", light_state=cached)
    assert r["params"]["keyPath"] == ["device", "light"]
    assert r["params"]["light"]["timePeriod"][0]["brightness"] == 80


def test_light_schedule_brightness_clamped():
    r = translate_command("light", "999", "AABBCC", "uid1",
                          subfield="schedule_brightness", light_state=_light_block())
    assert r["params"]["light"]["timePeriod"][0]["brightness"] == 100


def test_light_schedule_start_parses_hhmm():
    r = translate_command("light", "06:30", "AABBCC", "uid1",
                          subfield="schedule_start", light_state=_light_block())
    assert r["params"]["light"]["timePeriod"][0]["startTime"] == 6 * 3600 + 30 * 60


def test_light_schedule_end_parses_hhmm():
    r = translate_command("light", "20:00", "AABBCC", "uid1",
                          subfield="schedule_end", light_state=_light_block())
    assert r["params"]["light"]["timePeriod"][0]["endTime"] == 20 * 3600


def test_light_fade_minutes_to_seconds():
    r = translate_command("light", "15", "AABBCC", "uid1",
                          subfield="fade_minutes", light_state=_light_block())
    assert r["params"]["light"]["timePeriod"][0]["fadeTime"] == 900


def test_light_dim_threshold_writes_dark_temp():
    r = translate_command("light", "27.5", "AABBCC", "uid1",
                          subfield="dim_threshold", light_state=_light_block())
    assert r["params"]["light"]["darkTemp"] == 27.5


def test_light_off_threshold_writes_off_temp():
    r = translate_command("light", "30", "AABBCC", "uid1",
                          subfield="off_threshold", light_state=_light_block())
    assert r["params"]["light"]["offTemp"] == 30.0


def test_light_ppfd_target_writes_ppfd_period_brightness():
    r = translate_command("light", "650", "AABBCC", "uid1",
                          subfield="ppfd_target", light_state=_light_block())
    assert r["params"]["light"]["ppfdPeriod"][0]["brightness"] == 650


def test_light_ppfd_target_clamped_to_1000():
    r = translate_command("light", "9999", "AABBCC", "uid1",
                          subfield="ppfd_target", light_state=_light_block())
    assert r["params"]["light"]["ppfdPeriod"][0]["brightness"] == 1000


def test_light_ppfd_min_max_clamped_to_100():
    rmin = translate_command("light", "150", "AABBCC", "uid1",
                             subfield="ppfd_min", light_state=_light_block())
    rmax = translate_command("light", "200", "AABBCC", "uid1",
                             subfield="ppfd_max", light_state=_light_block())
    assert rmin["params"]["light"]["ppfdMinBrightness"] == 100
    assert rmax["params"]["light"]["ppfdMaxBrightness"] == 100


def test_light_ppfd_start_end_parses_hhmm():
    rs = translate_command("light", "07:15", "AABBCC", "uid1",
                           subfield="ppfd_start", light_state=_light_block())
    re = translate_command("light", "19:45", "AABBCC", "uid1",
                           subfield="ppfd_end", light_state=_light_block())
    assert rs["params"]["light"]["ppfdPeriod"][0]["startTime"] == 7 * 3600 + 15 * 60
    assert re["params"]["light"]["ppfdPeriod"][0]["endTime"] == 19 * 3600 + 45 * 60


def test_light_ppfd_fade_minutes_to_seconds():
    r = translate_command("light", "5", "AABBCC", "uid1",
                          subfield="ppfd_fade_minutes", light_state=_light_block())
    assert r["params"]["light"]["ppfdPeriod"][0]["fadeTime"] == 300


def test_light_subfield_with_empty_cache_synthesizes_default_block():
    # No cached block — translator must still produce a valid setConfigField.
    # Otherwise the controller silently rejects partial writes.
    r = translate_command("light", "07:00", "AABBCC", "uid1",
                          subfield="schedule_start", light_state={})
    assert r is not None
    blk = r["params"]["light"]
    assert blk["timePeriod"][0]["startTime"] == 7 * 3600
    # Synthesized defaults present
    assert "ppfdPeriod" in blk
    assert "darkTemp" in blk


def test_light_subfield_preserves_cached_block_other_fields():
    cached = _light_block(modeType=12, mLevel=50)
    r = translate_command("light", "55", "AABBCC", "uid1",
                          subfield="ppfd_min", light_state=cached)
    out = r["params"]["light"]
    # Changed
    assert out["ppfdMinBrightness"] == 55
    # Untouched
    assert out["modeType"] == 12
    assert out["mLevel"] == 50
    assert out["timePeriod"][0]["brightness"] == 65


def test_light2_subfield_targets_light2_keypath():
    r = translate_command("light2", "08:00", "AABBCC", "uid1",
                          subfield="schedule_start",
                          light_state={"light2": {"timePeriod": [{}]}})
    assert r["params"]["keyPath"] == ["device", "light2"]
    assert "light2" in r["params"]


def test_light_invalid_numeric_subfield_returns_none():
    r = translate_command("light", "abc", "AABBCC", "uid1",
                          subfield="schedule_brightness", light_state=_light_block())
    assert r is None


def test_fan_subfield_preserves_cached_block_other_fields():
    cached = {"fan": {
        "modeType": 2, "mOnOff": 1, "mLevel": 3,
        "shakeLevel": 6, "natural": 1,
        "minSpeed": 1, "maxSpeed": 5,
        "timePeriod": [{"enabled": 1, "weekmask": 127,
                        "startTime": 3600, "endTime": 7200}],
        "cycleTime": {"weekmask": 127, "startTime": 10800,
                      "openDur": 600, "closeDur": 1200, "times": 5},
    }}
    r = translate_command("fan", "20", "AABBCC", "uid1",
                          subfield="cycle_run_minutes", fan_state=cached)
    out = r["params"]["fan"]
    # Changed
    assert out["cycleTime"]["openDur"] == 1200
    # Untouched
    assert out["cycleTime"]["closeDur"] == 1200
    assert out["cycleTime"]["times"] == 5
    assert out["modeType"] == 2
    assert out["maxSpeed"] == 5
    assert out["natural"] == 1
