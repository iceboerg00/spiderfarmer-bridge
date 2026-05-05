import json
import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)

_TIME_PERIOD = [{"weekmask": 127}]

# Reverse mapping of the fan modeType labels surfaced as preset_modes in HA.
# Order here matches the SF App dropdown so the HA UI lists modes in the
# same order the user sees in the App.
_FAN_MODE_TO_TYPE = {
    "Manual": 0,
    "Schedule": 1,
    "Cycle": 2,
    "Environment: Prioritize temperature": 7,
    "Environment: Prioritize humidity": 8,
    "Environment: Temperature only": 3,
    "Environment: Humidity only": 4,
    "Environment: Temperature & humidity": 13,
}

# Submode-only labels for the Environment Mode sub-device dropdown. Same
# modeType space as preset_mode, just without the "Environment: " prefix
# (the card name already implies it).
_FAN_ENV_SUBMODE_TO_TYPE = {
    "Prioritize temperature": 7,
    "Prioritize humidity": 8,
    "Temperature only": 3,
    "Humidity only": 4,
    "Temperature & humidity": 13,
}


def _onoff(v) -> int:
    return 1 if str(v).upper() in ("ON", "1", "TRUE") else 0


def _hhmm_to_seconds(s) -> int:
    """Parse 'HH:MM' to seconds since midnight; 0 on parse error."""
    try:
        parts = str(s).split(":")
        h = int(parts[0])
        m = int(parts[1]) if len(parts) > 1 else 0
        return (h * 3600 + m * 60) % 86400
    except (ValueError, IndexError):
        return 0


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
    fan_state: Optional[dict] = None,
    light_state: Optional[dict] = None,
) -> Optional[dict]:
    state = device_state or {}
    last_levels = last_nonzero_level or {}
    fans = fan_state or {}
    lights = light_state or {}

    # ── Outlet ────────────────────────────────────────────────────────────────
    # Minimal payload — the controller already has the schedule/watering
    # state, we only flip mOnOff and ensure manual mode. CB and PS5/PS10/LC
    # all accept this once the proxy targets the correct DOWN topic prefix
    # (handled in inject() via session.down_topic_prefix).
    if outlet_num is not None:
        ok = f"O{outlet_num}"
        return _build(mac, uid, "outlet", ok, {"modeType": 0, "mOnOff": _onoff(value)})

    # ── Light / Light2 — app-parity subfield writes ─────────────────────────
    # Mirror the SF App's "Lampe Einstellungen" screen. Each HA entity (text/
    # number/switch under /command/light/<subfield>/set) maps to one field on
    # the controller's light/light2 block. Merge the subfield into a copy of
    # the cached block so the rest of the lamp's settings stay intact. When
    # the cache is empty, synthesize a default block so the controller does
    # not silently reject the partial command.
    _LIGHT_SUBFIELDS = {
        "dim_threshold", "off_threshold",
        "schedule_brightness", "schedule_start", "schedule_end", "fade_minutes",
        "ppfd_target", "ppfd_start", "ppfd_end", "ppfd_fade_minutes",
        "ppfd_min", "ppfd_max",
    }
    if field in ("light", "light2") and subfield in _LIGHT_SUBFIELDS:
        cached = lights.get(field)
        if cached:
            block = dict(cached)
        else:
            cur = state.get(field, {})
            block = {
                "modeType": cur.get("modeType", 0),
                "lastAutoModeType": cur.get("lastAutoModeType", 0),
                "mOnOff": int(cur.get("on", cur.get("mOnOff", 0))),
                "mLevel": int(cur.get("level", cur.get("mLevel", 0))),
                "darkTemp": 0,
                "offTemp": 0,
                "timePeriod": [{"enabled": 1, "weekmask": 127,
                                "startTime": 0, "endTime": 0,
                                "brightness": 0, "fadeTime": 0}],
                "ppfdPeriod": [{"enabled": 0, "weekmask": 127,
                                "startTime": 0, "endTime": 0,
                                "brightness": 0, "fadeTime": 0}],
                "ppfdMinBrightness": 0,
                "ppfdMaxBrightness": 100,
            }
            logger.info(
                "Light cache empty — using synthesized defaults for %s/%s",
                field, subfield,
            )

        def _tp0():
            tp = block.setdefault("timePeriod", [{}])
            if not tp:
                tp.append({})
            return tp[0]

        def _pp0():
            pp = block.setdefault("ppfdPeriod", [{}])
            if not pp:
                pp.append({})
            return pp[0]

        if subfield == "dim_threshold":
            try:
                block["darkTemp"] = float(value)
            except (ValueError, TypeError):
                return None
        elif subfield == "off_threshold":
            try:
                block["offTemp"] = float(value)
            except (ValueError, TypeError):
                return None
        elif subfield == "schedule_brightness":
            try:
                _tp0()["brightness"] = max(0, min(100, int(float(value))))
            except (ValueError, TypeError):
                return None
        elif subfield == "schedule_start":
            _tp0()["startTime"] = _hhmm_to_seconds(value)
        elif subfield == "schedule_end":
            _tp0()["endTime"] = _hhmm_to_seconds(value)
        elif subfield == "fade_minutes":
            try:
                _tp0()["fadeTime"] = max(0, int(float(value))) * 60
            except (ValueError, TypeError):
                return None
        elif subfield == "ppfd_target":
            try:
                _pp0()["brightness"] = max(0, min(1000, int(float(value))))
            except (ValueError, TypeError):
                return None
        elif subfield == "ppfd_start":
            _pp0()["startTime"] = _hhmm_to_seconds(value)
        elif subfield == "ppfd_end":
            _pp0()["endTime"] = _hhmm_to_seconds(value)
        elif subfield == "ppfd_fade_minutes":
            try:
                _pp0()["fadeTime"] = max(0, int(float(value))) * 60
            except (ValueError, TypeError):
                return None
        elif subfield == "ppfd_min":
            try:
                block["ppfdMinBrightness"] = max(0, min(100, int(float(value))))
            except (ValueError, TypeError):
                return None
        elif subfield == "ppfd_max":
            try:
                block["ppfdMaxBrightness"] = max(0, min(100, int(float(value))))
            except (ValueError, TypeError):
                return None
        return _build(mac, uid, "device", field, block)

    # ── Light / Light2 ────────────────────────────────────────────────────────
    # The SF cloud always sends modeType=0 (Manual) for direct app control —
    # mode 1 (Timer) makes the controller follow the stored schedule and
    # ignore mOnOff/mLevel. Mirror the cloud's payload shape so HA actually
    # controls the lamp instead of fighting the schedule.
    # Mode label ↔ modeType, confirmed against SF App. Old "Manual / Timer"
    # alias kept so HA selects from previous installs still resolve.
    _EFFECT_TO_MODE = {
        "Manual": 0,
        "Schedule": 1,
        "PPFD": 12,
        "Modus: Manual / Timer": 0,
    }
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

    # ── Fan / Blower — app-parity subfield writes ───────────────────────────
    # New HA entities (preset_mode, schedule_*, cycle_*, schedule_speed,
    # standby_speed, oscillation_level, natural_wind) each map to one field
    # on the controller's fan/blower block. Merge the subfield into a copy
    # of the cached block so the rest of the controller's settings stay
    # intact. When the cache is empty, synthesize a sensible default block
    # so the controller does not silently reject the partial command.
    _FAN_SUBFIELDS = {
        "preset_mode", "env_submode",
        "schedule_start", "schedule_end",
        "schedule_speed", "standby_speed",
        "cycle_start", "cycle_run_minutes", "cycle_off_minutes", "cycle_times",
        "oscillation_level", "natural_wind",
    }
    if field in ("fan", "blower") and subfield in _FAN_SUBFIELDS:
        cached = fans.get(field)
        if cached:
            block = dict(cached)
        else:
            cur = state.get(field, {})
            block = {
                "modeType": cur.get("modeType", 0),
                "mOnOff": int(cur.get("on", cur.get("mOnOff", 0))),
                "mLevel": int(cur.get("level", cur.get("mLevel", 1))),
                "shakeLevel": int(cur.get("shakeLevel", 0)),
                "natural": 0,
                "minSpeed": 0,
                "maxSpeed": 1,
                "timePeriod": [{"enabled": 1, "weekmask": 127, "startTime": 0, "endTime": 0}],
                "cycleTime": {"weekmask": 127, "startTime": 0, "openDur": 0, "closeDur": 0, "times": 1},
            }
            logger.info(
                "[%s] Fan cache empty — using synthesized defaults for %s/%s",
                field, field, subfield,
            )

        if subfield == "preset_mode":
            mt = _FAN_MODE_TO_TYPE.get(value)
            if mt is None:
                logger.warning("Unknown fan preset_mode: %s", value)
                return None
            block["modeType"] = mt
        elif subfield == "env_submode":
            mt = _FAN_ENV_SUBMODE_TO_TYPE.get(value)
            if mt is None:
                logger.warning("Unknown fan env_submode: %s", value)
                return None
            block["modeType"] = mt
        elif subfield == "schedule_start":
            tp = block.setdefault("timePeriod", [{}])
            if not tp:
                tp.append({})
            tp[0]["startTime"] = _hhmm_to_seconds(value)
        elif subfield == "schedule_end":
            tp = block.setdefault("timePeriod", [{}])
            if not tp:
                tp.append({})
            tp[0]["endTime"] = _hhmm_to_seconds(value)
        elif subfield == "schedule_speed":
            # The controller uses different fields for the active speed
            # depending on mode: mLevel in Manual, maxSpeed in
            # Schedule/Cycle/Environment. Write both so a single HA "Speed"
            # entity actually changes the fan regardless of current mode.
            # Range is 1-10 for Fan Circulation, 1-100 for Fan Exhaust
            # (blower) — the discovery payload sets the same bounds in HA.
            speed_max = 100 if field == "blower" else 10
            try:
                v = max(1, min(speed_max, int(float(value))))
            except (ValueError, TypeError):
                return None
            block["maxSpeed"] = v
            block["mLevel"] = v
        elif subfield == "standby_speed":
            speed_max = 100 if field == "blower" else 10
            try:
                block["minSpeed"] = max(0, min(speed_max, int(float(value))))
            except (ValueError, TypeError):
                return None
        elif subfield == "cycle_start":
            ct = block.setdefault("cycleTime", {"weekmask": 127})
            ct["startTime"] = _hhmm_to_seconds(value)
        elif subfield == "cycle_run_minutes":
            ct = block.setdefault("cycleTime", {"weekmask": 127})
            try:
                ct["openDur"] = max(0, int(float(value))) * 60
            except (ValueError, TypeError):
                return None
        elif subfield == "cycle_off_minutes":
            ct = block.setdefault("cycleTime", {"weekmask": 127})
            try:
                ct["closeDur"] = max(0, int(float(value))) * 60
            except (ValueError, TypeError):
                return None
        elif subfield == "cycle_times":
            ct = block.setdefault("cycleTime", {"weekmask": 127})
            try:
                # Controller hard-caps at 100 regardless of cycle duration.
                ct["times"] = max(1, min(100, int(float(value))))
            except (ValueError, TypeError):
                return None
        elif subfield == "oscillation_level":
            try:
                block["shakeLevel"] = max(0, min(10, int(float(value))))
            except (ValueError, TypeError):
                return None
        elif subfield == "natural_wind":
            block["natural"] = _onoff(value)
        # Force timePeriod[0].enabled = 1 on every fan write, regardless
        # of subfield. Observed bug: when the cache was seeded from a
        # getDevSta that omitted `enabled`, our optimistic re-publish (or
        # the Save button re-firing preset_mode) sent timePeriod without
        # enabled — the controller treated the schedule as disabled and
        # the trigger never fired until the user pressed Save in the SF
        # App, whose payload always includes enabled=1.
        tp = block.get("timePeriod")
        if isinstance(tp, list) and tp and isinstance(tp[0], dict):
            tp[0].setdefault("enabled", 1)
            tp[0].setdefault("weekmask", 127)
        return _build(mac, uid, "device", field, block)

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
