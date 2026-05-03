import json
import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)

_TIME_PERIOD = [{"weekmask": 127}]


def _onoff(v) -> int:
    return 1 if str(v).upper() in ("ON", "1", "TRUE") else 0


def _build(mac: str, uid: str, domain: str, module: str, obj: dict) -> dict:
    return {
        "method": "setConfigField",
        "pid": mac,
        "params": {"keyPath": [domain, module], module: obj},
        "msgId": str(int(time.time() * 1000)),
        "uid": uid,
    }


def translate_command(
    field: str,
    value: str,
    mac: str,
    uid: str,
    outlet_num: Optional[int] = None,
    device_state: Optional[dict] = None,
    subfield: Optional[str] = None,
    last_nonzero_level: Optional[dict] = None,
    outlet_state: Optional[dict] = None,
) -> Optional[dict]:
    state = device_state or {}
    last_levels = last_nonzero_level or {}
    outlets = outlet_state or {}

    # ── Outlet ────────────────────────────────────────────────────────────────
    # PS5/PS10 controllers reject minimal {modeType, mOnOff} commands. The
    # caller fetches the controller's current per-outlet config via
    # getConfigField and passes it in `outlet_state`; we spread that block
    # and override only modeType (force Manual) and mOnOff. This mirrors how
    # schedule-4-real's ha-bridge does it and works for any outlet shape
    # (simple, watering-bound, sensor-bound, etc.).
    # If outlet_state is missing (request failed or first-ever toggle),
    # fall back to the bare-minimum payload: works on CB, will be ignored
    # by PS5/PS10 but logs a warning upstream.
    if outlet_num is not None:
        ok = f"O{outlet_num}"
        cur = outlets.get(ok)
        if cur:
            block = dict(cur)
            block["modeType"] = 0
            block["mOnOff"] = _onoff(value)
            return _build(mac, uid, "outlet", ok, block)
        return _build(mac, uid, "outlet", ok, {"modeType": 0, "mOnOff": _onoff(value)})

    # ── Light / Light2 ────────────────────────────────────────────────────────
    # The SF cloud always sends modeType=0 (Manual) for direct app control —
    # mode 1 (Timer) makes the controller follow the stored schedule and
    # ignore mOnOff/mLevel. Mirror the cloud's payload shape so HA actually
    # controls the lamp instead of fighting the schedule.
    _EFFECT_TO_MODE = {"Modus: Manual / Timer": 0, "Modus: PPFD": 12}
    if field in ("light", "light2"):
        cur = state.get(field, {})
        try:
            cmd = json.loads(value)
        except (ValueError, TypeError):
            cmd = {"state": value}
        on = _onoff(cmd.get("state", "ON"))
        if "brightness" in cmd:
            level = int(cmd["brightness"])
        else:
            level = int(cur.get("level", cur.get("mLevel", 0)))
            # Controller reports level=0 while light is off; restore last
            # non-zero brightness so OFF→ON keeps the previous setting.
            if on == 1 and level == 0:
                level = int(last_levels.get(field, 100))
        level = max(0, min(100, level))
        mode = _EFFECT_TO_MODE.get(cmd.get("effect"), 0)
        return _build(mac, uid, "device", field, {
            "modeType": mode,
            "lastAutoModeType": cur.get("lastAutoModeType", 0),
            "mOnOff": on,
            "mLevel": level,
            "timePeriod": cur.get("timePeriod", _TIME_PERIOD),
        })

    # ── Blower on/off ─────────────────────────────────────────────────────────
    if field == "blower" and subfield is None:
        cur = state.get("blower", {})
        return _build(mac, uid, "device", "blower", {
            "mOnOff": _onoff(value),
            "mLevel": cur.get("level", cur.get("mLevel", 50)),
            "natural": 0,
            "timePeriod": _TIME_PERIOD,
        })

    # ── Blower percentage ─────────────────────────────────────────────────────
    if field == "blower" and subfield == "percentage":
        try:
            level = max(1, min(100, int(value)))
        except ValueError:
            return None
        cur = state.get("blower", {})
        return _build(mac, uid, "device", "blower", {
            "mOnOff": cur.get("on", cur.get("mOnOff", 1)),
            "mLevel": level,
            "natural": 0,
            "timePeriod": _TIME_PERIOD,
        })

    # ── Fan on/off ────────────────────────────────────────────────────────────
    if field == "fan" and subfield is None:
        cur = state.get("fan", {})
        return _build(mac, uid, "device", "fan", {
            "mOnOff": _onoff(value),
            "mLevel": cur.get("level", cur.get("mLevel", 5)),
            "shakeLevel": cur.get("shakeLevel", 0),
            "natural": 0,
            "timePeriod": _TIME_PERIOD,
        })

    # ── Fan percentage ────────────────────────────────────────────────────────
    if field == "fan" and subfield == "percentage":
        try:
            level = max(1, min(10, int(value)))
        except ValueError:
            return None
        cur = state.get("fan", {})
        return _build(mac, uid, "device", "fan", {
            "mOnOff": cur.get("on", cur.get("mOnOff", 1)),
            "mLevel": level,
            "shakeLevel": cur.get("shakeLevel", 0),
            "natural": 0,
            "timePeriod": _TIME_PERIOD,
        })

    # ── Climate accessories ───────────────────────────────────────────────────
    if field in ("heater", "humidifier", "dehumidifier"):
        cur = state.get(field, {})
        return _build(mac, uid, "device", field, {
            "mOnOff": _onoff(value),
            "mLevel": cur.get("level", cur.get("mLevel", 0)),
            "timePeriod": _TIME_PERIOD,
        })

    logger.warning("Unknown command field: %s subfield: %s", field, subfield)
    return None
