import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)


def _onoff(v: str) -> int:
    return 1 if str(v).upper() in ("ON", "1", "TRUE") else 0


def _build_payload(mac: str, uid: str, module: str, module_obj: dict) -> dict:
    return {
        "method": "setConfigField",
        "params": {
            "keyPath": ["device" if module != "outlet" else "outlet", module],
            module: module_obj,
        },
        "pid": mac,
        "msgId": str(int(time.time() * 1000)),
        "uid": uid,
        "UTC": int(time.time()),
    }


def translate_command(
    field: str,
    value: str,
    mac: str,
    uid: str,
    outlet_num: Optional[int] = None,
    device_state: Optional[dict] = None,
) -> Optional[dict]:
    state = device_state or {}

    # ── Outlet ────────────────────────────────────────────────────────────────
    if outlet_num is not None:
        ok = f"O{outlet_num}"
        cur = state.get("outlet", {}).get(ok, {})
        obj = {**cur, "modeType": cur.get("modeType", 0), "mOnOff": _onoff(value)}
        payload = {
            "method": "setConfigField",
            "params": {"keyPath": ["outlet", ok], ok: obj},
            "pid": mac,
            "msgId": str(int(time.time() * 1000)),
            "uid": uid,
            "UTC": int(time.time()),
        }
        return payload

    # ── Light ─────────────────────────────────────────────────────────────────
    if field == "light_on":
        cur = state.get("light", {})
        obj = {
            "modeType": cur.get("modeType", 1),
            "mOnOff": _onoff(value),
            "mLevel": cur.get("level", cur.get("mLevel", 50)),
        }
        return _build_payload(mac, uid, "light", obj)

    if field == "light_1_brightness":
        try:
            level = max(0, min(100, int(value)))
        except ValueError:
            return None
        cur = state.get("light", {})
        obj = {
            "modeType": cur.get("modeType", 1),
            "mOnOff": cur.get("on", cur.get("mOnOff", 1)),
            "mLevel": level,
        }
        return _build_payload(mac, uid, "light", obj)

    # ── Blower ────────────────────────────────────────────────────────────────
    if field == "blower_on":
        cur = state.get("blower", {})
        obj = {
            "modeType": cur.get("modeType", 0),
            "mOnOff": _onoff(value),
            "mLevel": cur.get("level", cur.get("mLevel", 50)),
            "minSpeed": cur.get("minSpeed", 0),
            "maxSpeed": cur.get("maxSpeed", 0),
            "closeCO2": cur.get("closeCO2", 0),
        }
        return _build_payload(mac, uid, "blower", obj)

    if field == "blower_speed":
        try:
            level = max(0, min(100, int(value)))
        except ValueError:
            return None
        cur = state.get("blower", {})
        obj = {
            "modeType": cur.get("modeType", 0),
            "mOnOff": cur.get("on", cur.get("mOnOff", 1)),
            "mLevel": level,
            "minSpeed": cur.get("minSpeed", 0),
            "maxSpeed": cur.get("maxSpeed", 0),
            "closeCO2": cur.get("closeCO2", 0),
        }
        return _build_payload(mac, uid, "blower", obj)

    # ── Fan ───────────────────────────────────────────────────────────────────
    if field == "fan_on":
        cur = state.get("fan", {})
        obj = {
            "modeType": cur.get("modeType", 0),
            "mOnOff": _onoff(value),
            "mLevel": cur.get("level", cur.get("mLevel", 5)),
            "minSpeed": cur.get("minSpeed", 0),
            "maxSpeed": cur.get("maxSpeed", 0),
            "shakeLevel": cur.get("shakeLevel", 0),
            "natural": cur.get("natural", 0),
        }
        return _build_payload(mac, uid, "fan", obj)

    if field == "fan_speed":
        try:
            level = max(0, min(10, int(value)))
        except ValueError:
            return None
        cur = state.get("fan", {})
        obj = {
            "modeType": cur.get("modeType", 0),
            "mOnOff": cur.get("on", cur.get("mOnOff", 1)),
            "mLevel": level,
            "minSpeed": cur.get("minSpeed", 0),
            "maxSpeed": cur.get("maxSpeed", 0),
            "shakeLevel": cur.get("shakeLevel", 0),
            "natural": cur.get("natural", 0),
        }
        return _build_payload(mac, uid, "fan", obj)

    # ── Climate accessories ───────────────────────────────────────────────────
    if field in ("heater", "humidifier", "dehumidifier"):
        cur = state.get(field, {})
        obj = {
            "modeType": cur.get("modeType", 0),
            "mOnOff": _onoff(value),
            "mLevel": cur.get("level", cur.get("mLevel", 0)),
        }
        return _build_payload(mac, uid, field, obj)

    logger.warning("Unknown command field: %s", field)
    return None
