import json
import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)


def _onoff(v) -> int:
    return 1 if str(v).upper() in ("ON", "1", "TRUE") else 0


def _build(mac: str, uid: str, domain: str, module: str, obj: dict) -> dict:
    return {
        "method": "setConfigField",
        "params": {"keyPath": [domain, module], module: obj},
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
    subfield: Optional[str] = None,
) -> Optional[dict]:
    state = device_state or {}

    # ── Outlet ────────────────────────────────────────────────────────────────
    if outlet_num is not None:
        ok = f"O{outlet_num}"
        cur = state.get("outlet", {}).get(ok, {})
        return _build(mac, uid, "outlet", ok,
                      {**cur, "modeType": cur.get("modeType", 0), "mOnOff": _onoff(value)})

    # ── Light / Light2 (JSON schema) ──────────────────────────────────────────
    _EFFECT_TO_MODE = {"Manual / Timer": 1, "PPFD": 12}
    if field in ("light", "light2"):
        cur = state.get(field, {})
        try:
            cmd = json.loads(value)
        except (ValueError, TypeError):
            cmd = {"state": value}
        on = _onoff(cmd.get("state", "ON"))
        level = int(cmd.get("brightness", cur.get("level", cur.get("mLevel", 50))))
        level = max(0, min(100, level))
        effect = cmd.get("effect")
        mode = _EFFECT_TO_MODE.get(effect, cur.get("modeType", 1)) if effect else cur.get("modeType", 1)
        return _build(mac, uid, "device", field, {
            "modeType": mode,
            "mOnOff": on,
            "mLevel": level,
        })

    # ── Blower on/off ─────────────────────────────────────────────────────────
    if field == "blower" and subfield is None:
        cur = state.get("blower", {})
        return _build(mac, uid, "device", "blower", {
            "modeType": cur.get("modeType", 0),
            "mOnOff": _onoff(value),
            "mLevel": cur.get("level", cur.get("mLevel", 50)),
            "minSpeed": cur.get("minSpeed", 0),
            "maxSpeed": cur.get("maxSpeed", 0),
            "closeCO2": cur.get("closeCO2", 0),
        })

    # ── Blower percentage ─────────────────────────────────────────────────────
    if field == "blower" and subfield == "percentage":
        try:
            level = max(1, min(100, int(value)))
        except ValueError:
            return None
        cur = state.get("blower", {})
        return _build(mac, uid, "device", "blower", {
            "modeType": cur.get("modeType", 0),
            "mOnOff": cur.get("on", cur.get("mOnOff", 1)),
            "mLevel": level,
            "minSpeed": cur.get("minSpeed", 0),
            "maxSpeed": cur.get("maxSpeed", 0),
            "closeCO2": cur.get("closeCO2", 0),
        })

    # ── Fan on/off ────────────────────────────────────────────────────────────
    if field == "fan" and subfield is None:
        cur = state.get("fan", {})
        return _build(mac, uid, "device", "fan", {
            "modeType": cur.get("modeType", 0),
            "mOnOff": _onoff(value),
            "mLevel": cur.get("level", cur.get("mLevel", 5)),
            "minSpeed": cur.get("minSpeed", 0),
            "maxSpeed": cur.get("maxSpeed", 0),
            "shakeLevel": cur.get("shakeLevel", 0),
            "natural": cur.get("natural", 0),
        })

    # ── Fan percentage ────────────────────────────────────────────────────────
    if field == "fan" and subfield == "percentage":
        try:
            level = max(1, min(10, int(value)))
        except ValueError:
            return None
        cur = state.get("fan", {})
        return _build(mac, uid, "device", "fan", {
            "modeType": cur.get("modeType", 0),
            "mOnOff": cur.get("on", cur.get("mOnOff", 1)),
            "mLevel": level,
            "minSpeed": cur.get("minSpeed", 0),
            "maxSpeed": cur.get("maxSpeed", 0),
            "shakeLevel": cur.get("shakeLevel", 0),
            "natural": cur.get("natural", 0),
        })

    # ── Fan oscillation ───────────────────────────────────────────────────────
    if field == "fan" and subfield == "oscillation":
        shake = 1 if value == "oscillate_on" else 0
        cur = state.get("fan", {})
        return _build(mac, uid, "device", "fan", {
            "modeType": cur.get("modeType", 0),
            "mOnOff": cur.get("on", cur.get("mOnOff", 1)),
            "mLevel": cur.get("level", cur.get("mLevel", 5)),
            "minSpeed": cur.get("minSpeed", 0),
            "maxSpeed": cur.get("maxSpeed", 0),
            "shakeLevel": shake,
            "natural": cur.get("natural", 0),
        })

    # ── Climate accessories ───────────────────────────────────────────────────
    if field in ("heater", "humidifier", "dehumidifier"):
        cur = state.get(field, {})
        return _build(mac, uid, "device", field, {
            "modeType": cur.get("modeType", 0),
            "mOnOff": _onoff(value),
            "mLevel": cur.get("level", cur.get("mLevel", 0)),
        })

    logger.warning("Unknown command field: %s subfield: %s", field, subfield)
    return None
