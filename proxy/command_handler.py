import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)

# (domain, module_key, param_key, converter)
def _onoff(v: str) -> int:
    return 1 if str(v).upper() in ("ON", "1", "TRUE") else 0


_COMMAND_MAP = {
    "light_on":           ("device", "light",        "mOnOff", _onoff),
    "light_1_brightness": ("device", "light",        "mLevel", int),
    "blower_on":          ("device", "blower",       "mOnOff", _onoff),
    "blower_speed":       ("device", "blower",       "mLevel", int),
    "fan_on":             ("device", "fan",           "mOnOff", _onoff),
    "fan_speed":          ("device", "fan",           "mLevel", int),
    "heater":             ("device", "heater",        "mOnOff", _onoff),
    "humidifier":         ("device", "humidifier",   "mOnOff", _onoff),
    "dehumidifier":       ("device", "dehumidifier", "mOnOff", _onoff),
}

_RANGES = {
    "blower_speed":       (0, 100),
    "fan_speed":          (0, 10),
    "light_1_brightness": (0, 100),
}


def translate_command(
    field: str,
    value: str,
    mac: str,
    uid: str,
    outlet_num: Optional[int] = None,
) -> Optional[dict]:
    """
    Translate a normalized HA command to Spider Farmer setConfigField payload.
    Returns dict or None if field is unknown or value is invalid/out-of-range.
    """
    now = int(time.time())

    if outlet_num is not None:
        on_val = 1 if str(value).upper() in ("ON", "1") else 0
        ok = f"O{outlet_num}"
        return {
            "method": "setConfigField",
            "params": {"keyPath": ["outlet", ok], ok: {"mOnOff": on_val}},
            "pid": mac,
            "msgId": int(time.time() * 1000),
            "uid": uid,
            "UTC": now,
        }

    if field not in _COMMAND_MAP:
        logger.warning("Unknown command field: %s", field)
        return None

    domain, module_key, param_key, converter = _COMMAND_MAP[field]

    try:
        converted = converter(value)
    except (ValueError, TypeError) as e:
        logger.warning("Invalid value %r for %s: %s", value, field, e)
        return None

    if field in _RANGES:
        lo, hi = _RANGES[field]
        if not (lo <= converted <= hi):
            logger.warning("Value %s out of range [%s, %s] for %s", converted, lo, hi, field)
            return None

    return {
        "method": "setConfigField",
        "params": {"keyPath": [domain, module_key], module_key: {param_key: converted}},
        "pid": mac,
        "msgId": int(time.time() * 1000),
        "uid": uid,
        "UTC": now,
    }
