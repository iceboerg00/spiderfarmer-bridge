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
    """Convert Spider Farmer on/off values to ON/OFF string."""
    return "ON" if val in (1, True, "1", "true", "on") else "OFF"


def normalize_sensors(device_id: str, data: Dict[str, Any]) -> Dict[str, str]:
    """Map ggs/.../sensors payload to normalized topics."""
    result: Dict[str, str] = {}
    for sf_key, norm_key in _SENSOR_FIELD_MAP:
        if sf_key in data:
            result[f"spiderfarmer/{device_id}/state/{norm_key}"] = str(data[sf_key])
    return result


def normalize_status(device_id: str, data: Dict[str, Any]) -> Dict[str, str]:
    """Map ggs/.../status payload to normalized topics."""
    result: Dict[str, str] = {}
    d = data.get("data", data)  # handle wrapped and unwrapped payloads

    # Environmental sensor block inside status
    sensor = d.get("sensor", {})
    for sf_key, norm_key in _SENSOR_FIELD_MAP:
        if sf_key in sensor:
            result[f"spiderfarmer/{device_id}/state/{norm_key}"] = str(sensor[sf_key])

    # Blower
    blower = d.get("blower", {})
    if blower:
        level = blower.get("mLevel", blower.get("level"))
        if level is not None:
            result[f"spiderfarmer/{device_id}/state/blower_speed"] = str(level)
        on = blower.get("mOnOff", blower.get("on"))
        if on is not None:
            result[f"spiderfarmer/{device_id}/state/blower_on"] = _on_off(on)

    # Fan
    fan = d.get("fan", {})
    if fan:
        level = fan.get("mLevel", fan.get("level"))
        if level is not None:
            result[f"spiderfarmer/{device_id}/state/fan_speed"] = str(level)
        on = fan.get("mOnOff", fan.get("on"))
        if on is not None:
            result[f"spiderfarmer/{device_id}/state/fan_on"] = _on_off(on)

    # Light 1
    light = d.get("light", {})
    if light:
        level = light.get("mLevel", light.get("level"))
        if level is not None:
            result[f"spiderfarmer/{device_id}/state/light_1_brightness"] = str(level)
        on = light.get("mOnOff", light.get("on"))
        if on is not None:
            result[f"spiderfarmer/{device_id}/state/light_on"] = _on_off(on)

    # Light 2
    light2 = d.get("light2", {})
    if light2:
        level = light2.get("mLevel", light2.get("level"))
        if level is not None:
            result[f"spiderfarmer/{device_id}/state/light_2_brightness"] = str(level)

    # Heater, Humidifier, Dehumidifier
    for module, state_key in [
        ("heater", "heater"),
        ("humidifier", "humidifier"),
        ("dehumidifier", "dehumidifier"),
    ]:
        mod = d.get(module, {})
        if mod:
            on = mod.get("mOnOff", mod.get("on"))
            if on is not None:
                result[f"spiderfarmer/{device_id}/state/{state_key}"] = _on_off(on)

    # Individual soil sensors — keyed by hardware ID
    for s in d.get("sensors", []):
        sid = s.get("id")
        if not sid or sid == "avg":
            continue
        for sf_key, norm_key in [("tempSoil", "temp"), ("humiSoil", "humi"), ("ECSoil", "ec")]:
            if sf_key in s:
                result[f"spiderfarmer/{device_id}/state/soil_{sid}_{norm_key}"] = str(s[sf_key])

    # Outlets O1..ON
    outlet = d.get("outlet", {})
    for key, val in outlet.items():
        if key.startswith("O") and key[1:].isdigit():
            num = key[1:]
            on = val.get("mOnOff", val.get("on"))
            if on is not None:
                result[f"spiderfarmer/{device_id}/state/outlet_{num}"] = _on_off(on)

    return result
