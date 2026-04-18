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


def _on_off(val) -> str:
    return "ON" if val in (1, True, "1", "true", "on") else "OFF"


def normalize_status(device_id: str, data: Dict[str, Any]) -> Dict[str, str]:
    result: Dict[str, str] = {}
    d = data.get("data", data)

    # ── Air sensors ───────────────────────────────────────────────────────────
    sensor = d.get("sensor", {})
    for sf_key, norm_key in _SENSOR_FIELD_MAP:
        if sf_key in sensor:
            result[f"spiderfarmer/{device_id}/state/{norm_key}"] = str(sensor[sf_key])

    # ── Light (JSON schema with effect for mode) ──────────────────────────────
    _LIGHT_MODES = {1: "Manual / Timer", 12: "PPFD"}
    light = d.get("light", {})
    if light:
        mode = light.get("modeType", 1)
        result[f"spiderfarmer/{device_id}/state/light"] = json.dumps({
            "state": _on_off(light.get("on", light.get("mOnOff", 0))),
            "brightness": light.get("level", light.get("mLevel", 0)),
            "effect": _LIGHT_MODES.get(mode, str(mode)),
        })

    light2 = d.get("light2", {})
    if light2:
        mode2 = light2.get("modeType", 1)
        result[f"spiderfarmer/{device_id}/state/light2"] = json.dumps({
            "state": _on_off(light2.get("on", light2.get("mOnOff", 0))),
            "brightness": light2.get("level", light2.get("mLevel", 0)),
            "effect": _LIGHT_MODES.get(mode2, str(mode2)),
        })

    # ── Blower (JSON state) ───────────────────────────────────────────────────
    blower = d.get("blower", {})
    if blower:
        result[f"spiderfarmer/{device_id}/state/blower"] = json.dumps({
            "state": _on_off(blower.get("on", blower.get("mOnOff", 0))),
            "percentage": blower.get("level", blower.get("mLevel", 0)),
        })

    # ── Fan (JSON state + oscillation) ────────────────────────────────────────
    fan = d.get("fan", {})
    if fan:
        shake = fan.get("shakeLevel", 0)
        result[f"spiderfarmer/{device_id}/state/fan"] = json.dumps({
            "state": _on_off(fan.get("on", fan.get("mOnOff", 0))),
            "percentage": fan.get("level", fan.get("mLevel", 0)),
            "oscillating": shake > 0,
        })
        result[f"spiderfarmer/{device_id}/state/fan_shake"] = str(shake)

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
