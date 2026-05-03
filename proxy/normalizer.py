import json
from typing import Dict, Any


_SENSOR_FIELD_MAP = [
    ("temp", "temperature"),
    ("humi", "humidity"),
    ("vpd", "vpd"),
    ("co2", "co2"),
    ("ppfd", "ppfd"),
    ("tempSoil", "temp_soil"),
    ("humiSoil", "humi_soil"),
    ("ECSoil", "ec_soil"),
]

# modeType values for the fan block — confirmed from cloud setConfigField
# captures while clicking through every mode in the SF App. The five Umwelt-
# variants share modeType space with Manuell/Zeitfenster/Zyklus rather than
# living in a separate Betriebsmodus field.
_FAN_MODES = {
    0: "Manual",
    1: "Schedule",
    2: "Cycle",
    3: "Environment: Temperature only",
    4: "Environment: Humidity only",
    7: "Environment: Prioritize temperature",
    8: "Environment: Prioritize humidity",
    13: "Environment: Temperature & humidity",
}

# Subset for the Environment Mode sub-device dropdown — the SF App's
# Umweltmodus tab only lets you switch between the 5 env variants, so the
# state topic for that select entity drops the "Environment: " prefix
# (which is already implied by the card name) and stays empty when the fan
# is in Manual/Schedule/Cycle.
_FAN_ENV_LABELS = {
    3: "Temperature only",
    4: "Humidity only",
    7: "Prioritize temperature",
    8: "Prioritize humidity",
    13: "Temperature & humidity",
}


def _on_off(val) -> str:
    return "ON" if val in (1, True, "1", "true", "on") else "OFF"


def _seconds_to_hhmm(seconds) -> str:
    try:
        s = int(seconds) % 86400
    except (TypeError, ValueError):
        return "00:00"
    return f"{s // 3600:02d}:{(s % 3600) // 60:02d}"


def light_extras_topics(device_id: str, prefix: str, block: Dict[str, Any]) -> Dict[str, str]:
    """Per-field state topics for a light/light2 block. Used both by
    normalize_status when getDevSta arrives and by relay_down / handle_command
    after a setConfigField is observed/sent so the new HA entities populate
    immediately. Mirror of fan_extras_topics, just for the light schema."""
    out: Dict[str, str] = {}
    if not isinstance(block, dict):
        return out
    base = f"spiderfarmer/{device_id}/state/{prefix}"
    if "darkTemp" in block:
        out[f"{base}/dim_threshold"] = str(block["darkTemp"])
    if "offTemp" in block:
        out[f"{base}/off_threshold"] = str(block["offTemp"])
    # Schedule (Zeitfenstermodus) — timePeriod[0]
    periods = block.get("timePeriod") or []
    if isinstance(periods, list) and periods:
        tp = periods[0] if isinstance(periods[0], dict) else {}
        if "brightness" in tp:
            out[f"{base}/schedule_brightness"] = str(tp["brightness"])
        if "startTime" in tp:
            out[f"{base}/schedule_start"] = _seconds_to_hhmm(tp["startTime"])
        if "endTime" in tp:
            out[f"{base}/schedule_end"] = _seconds_to_hhmm(tp["endTime"])
        if "fadeTime" in tp:
            try:
                out[f"{base}/fade_minutes"] = str(int(tp["fadeTime"]) // 60)
            except (TypeError, ValueError):
                pass
    # PPFD-Mode — own schedule + brightness limits
    ppfd_periods = block.get("ppfdPeriod") or []
    if isinstance(ppfd_periods, list) and ppfd_periods:
        pp = ppfd_periods[0] if isinstance(ppfd_periods[0], dict) else {}
        if "brightness" in pp:
            out[f"{base}/ppfd_target"] = str(pp["brightness"])
        if "startTime" in pp:
            out[f"{base}/ppfd_start"] = _seconds_to_hhmm(pp["startTime"])
        if "endTime" in pp:
            out[f"{base}/ppfd_end"] = _seconds_to_hhmm(pp["endTime"])
        if "fadeTime" in pp:
            try:
                out[f"{base}/ppfd_fade_minutes"] = str(int(pp["fadeTime"]) // 60)
            except (TypeError, ValueError):
                pass
    if "ppfdMinBrightness" in block:
        out[f"{base}/ppfd_min"] = str(block["ppfdMinBrightness"])
    if "ppfdMaxBrightness" in block:
        out[f"{base}/ppfd_max"] = str(block["ppfdMaxBrightness"])
    return out


def fan_extras_topics(device_id: str, prefix: str, block: Dict[str, Any]) -> Dict[str, str]:
    """Per-field state topics for a fan/blower block. Used by normalize_status
    when getDevSta arrives and by relay_down after observing a cloud
    setConfigField, so the new HA entities (preset_mode, schedule, cycle,
    speeds) get populated immediately."""
    out: Dict[str, str] = {}
    if not isinstance(block, dict):
        return out
    base = f"spiderfarmer/{device_id}/state/{prefix}"
    if "modeType" in block:
        mt = block["modeType"]
        out[f"{base}/mode_label"] = _FAN_MODES.get(mt, str(mt))
        # Empty string when not in env mode → HA select entity goes to
        # "unknown" rather than displaying a non-option like "Manual".
        out[f"{base}/env_submode"] = _FAN_ENV_LABELS.get(mt, "")
    if "maxSpeed" in block:
        out[f"{base}/schedule_speed"] = str(block["maxSpeed"])
    if "minSpeed" in block:
        out[f"{base}/standby_speed"] = str(block["minSpeed"])
    if "shakeLevel" in block:
        out[f"{base}/oscillation_level"] = str(block["shakeLevel"])
    if "natural" in block:
        out[f"{base}/natural_wind"] = _on_off(block["natural"])
    # Schedule-Modus (Zeitfenster) — timePeriod[0]
    periods = block.get("timePeriod") or []
    if isinstance(periods, list) and periods:
        tp = periods[0] if isinstance(periods[0], dict) else {}
        if "startTime" in tp:
            out[f"{base}/schedule_start"] = _seconds_to_hhmm(tp["startTime"])
        if "endTime" in tp:
            out[f"{base}/schedule_end"] = _seconds_to_hhmm(tp["endTime"])
    # Zyklusmodus
    ct = block.get("cycleTime")
    if isinstance(ct, dict):
        if "startTime" in ct:
            out[f"{base}/cycle_start"] = _seconds_to_hhmm(ct["startTime"])
        if "openDur" in ct:
            try:
                out[f"{base}/cycle_run_minutes"] = str(int(ct["openDur"]) // 60)
            except (TypeError, ValueError):
                pass
        if "closeDur" in ct:
            try:
                out[f"{base}/cycle_off_minutes"] = str(int(ct["closeDur"]) // 60)
            except (TypeError, ValueError):
                pass
        if "times" in ct:
            out[f"{base}/cycle_times"] = str(ct["times"])
    return out


def normalize_status(device_id: str, data: Dict[str, Any],
                     light_cache: Dict[str, dict] | None = None,
                     fan_cache: Dict[str, dict] | None = None) -> Dict[str, str]:
    result: Dict[str, str] = {}
    d = data.get("data", data)

    # ── Air sensors ───────────────────────────────────────────────────────────
    sensor = d.get("sensor", {})
    for sf_key, norm_key in _SENSOR_FIELD_MAP:
        if sf_key in sensor:
            result[f"spiderfarmer/{device_id}/state/{norm_key}"] = str(sensor[sf_key])

    # ── Light (JSON schema with effect for mode) ──────────────────────────────
    # Both modeType 0 (Manual) and 1 (Timer) map to the same UI label so the
    # effect dropdown in HA shows a known value regardless of which the
    # controller currently reports.
    # modeType values confirmed against the SF App.
    # 0 = Manual, 1 = Schedule (Zeitfenstermodus), 12 = PPFD.
    _LIGHT_MODES = {0: "Manual", 1: "Schedule", 12: "PPFD"}

    # Standalone Light Controller (LC) reports light state flat at the top
    # level — `data.brightness` + `data.mode` instead of nested under
    # `data.light.{level, modeType}`. Map it to the same `light` topic so
    # HA's light entity works without a separate code path.
    if "brightness" in d and "mode" in d and "light" not in d:
        lc_brightness = d.get("brightness", 0)
        lc_mode = d.get("mode", 1)
        result[f"spiderfarmer/{device_id}/state/light"] = json.dumps({
            "state": _on_off(1 if isinstance(lc_brightness, (int, float)) and lc_brightness > 0 else 0),
            "brightness": lc_brightness,
            "effect": _LIGHT_MODES.get(lc_mode, str(lc_mode)),
        })

    # Light blocks: getDevSta only carries {on, level} for some firmwares —
    # no modeType. Falling back to a hard-coded default would flip HA's
    # effect dropdown to the wrong mode whenever the controller sends a
    # status update. Prefer the cached modeType from observed setConfigField
    # traffic instead.
    lc = light_cache or {}

    light = d.get("light", {})
    if light:
        mode = light.get("modeType", lc.get("light", {}).get("modeType", 0))
        result[f"spiderfarmer/{device_id}/state/light"] = json.dumps({
            "state": _on_off(light.get("on", light.get("mOnOff", 0))),
            "brightness": light.get("level", light.get("mLevel", 0)),
            "effect": _LIGHT_MODES.get(mode, str(mode)),
        })
        # Merge cached schedule/ppfd/temp fields into the block we hand to
        # light_extras_topics — getDevSta on its own only carries on/level
        # and would yield empty entities until the next setConfigField.
        merged = {**lc.get("light", {}), **light}
        result.update(light_extras_topics(device_id, "light", merged))

    light2 = d.get("light2", {})
    if light2:
        mode2 = light2.get("modeType", lc.get("light2", {}).get("modeType", 0))
        result[f"spiderfarmer/{device_id}/state/light2"] = json.dumps({
            "state": _on_off(light2.get("on", light2.get("mOnOff", 0))),
            "brightness": light2.get("level", light2.get("mLevel", 0)),
            "effect": _LIGHT_MODES.get(mode2, str(mode2)),
        })
        merged2 = {**lc.get("light2", {}), **light2}
        result.update(light_extras_topics(device_id, "light2", merged2))

    # ── Blower (JSON state) ───────────────────────────────────────────────────
    blower = d.get("blower", {})
    if blower:
        result[f"spiderfarmer/{device_id}/state/blower"] = json.dumps({
            "state": _on_off(blower.get("on", blower.get("mOnOff", 0))),
            "percentage": blower.get("level", blower.get("mLevel", 0)),
        })
        result.update(fan_extras_topics(device_id, "blower", blower))

    # ── Fan (JSON state + oscillation) ────────────────────────────────────────
    fan = d.get("fan", {})
    if fan:
        result[f"spiderfarmer/{device_id}/state/fan"] = json.dumps({
            "state": _on_off(fan.get("on", fan.get("mOnOff", 0))),
            "percentage": fan.get("level", fan.get("mLevel", 0)),
        })
        result.update(fan_extras_topics(device_id, "fan", fan))

    # ── Accessories ───────────────────────────────────────────────────────────
    for module in ("heater", "humidifier", "dehumidifier"):
        mod = d.get(module, {})
        if mod:
            on = mod.get("mOnOff", mod.get("on"))
            if on is not None:
                result[f"spiderfarmer/{device_id}/state/{module}"] = _on_off(on)

    # ── Individual soil sensors ───────────────────────────────────────────────
    for s in d.get("sensors", []):
        sid = s.get("id")
        if not sid or sid == "avg":
            continue
        for sf_key, norm_key in [("tempSoil", "temp"), ("humiSoil", "humi"), ("ECSoil", "ec")]:
            if sf_key in s:
                result[f"spiderfarmer/{device_id}/state/soil_{sid}_{norm_key}"] = str(s[sf_key])

    # ── Outlets ───────────────────────────────────────────────────────────────
    for key, val in d.get("outlet", {}).items():
        if key.startswith("O") and key[1:].isdigit():
            on = val.get("mOnOff", val.get("on"))
            if on is not None:
                result[f"spiderfarmer/{device_id}/state/outlet_{key[1:]}"] = _on_off(on)

    return result
