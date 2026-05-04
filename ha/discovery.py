import json
import logging
from typing import Tuple

import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)


def _device_info(device_id: str, cfg: dict) -> dict:
    return {
        "identifiers": [f"spiderfarmer_{device_id}"],
        "name": cfg.get("friendly_name", f"Spider Farmer {device_id}"),
        "manufacturer": "Spider Farmer",
        "model": "GGS Controller",
    }


def _sensor(device_id: str, field: str, name: str, unit: str, device_class: str | None, cfg: dict) -> Tuple[str, dict]:
    uid = f"spiderfarmer_{device_id}_{field}"
    payload: dict = {
        "name": name,
        "unique_id": uid,
        "state_topic": f"spiderfarmer/{device_id}/state/{field}",
        "availability_topic": f"spiderfarmer/{device_id}/availability",
        "state_class": "measurement",
        "device": _device_info(device_id, cfg),
    }
    if unit:
        payload["unit_of_measurement"] = unit
    if device_class:
        payload["device_class"] = device_class
    return f"homeassistant/sensor/{uid}/config", payload


def _number(device_id: str, field: str, name: str, min_val: int, max_val: int, cfg: dict) -> Tuple[str, dict]:
    uid = f"spiderfarmer_{device_id}_{field}"
    payload = {
        "name": name,
        "unique_id": uid,
        "state_topic": f"spiderfarmer/{device_id}/state/{field}",
        "command_topic": f"spiderfarmer/{device_id}/command/{field}/set",
        "availability_topic": f"spiderfarmer/{device_id}/availability",
        "min": min_val,
        "max": max_val,
        "step": 1,
        "device": _device_info(device_id, cfg),
    }
    return f"homeassistant/number/{uid}/config", payload


def _switch(device_id: str, field: str, name: str, cfg: dict) -> Tuple[str, dict]:
    uid = f"spiderfarmer_{device_id}_{field}"
    payload = {
        "name": name,
        "unique_id": uid,
        "state_topic": f"spiderfarmer/{device_id}/state/{field}",
        "command_topic": f"spiderfarmer/{device_id}/command/{field}/set",
        "availability_topic": f"spiderfarmer/{device_id}/availability",
        "payload_on": "ON",
        "payload_off": "OFF",
        "device": _device_info(device_id, cfg),
    }
    return f"homeassistant/switch/{uid}/config", payload


def _number_path(device_id: str, path: str, suffix: str, name: str,
                 min_val, max_val, step, cfg: dict, unit: str | None = None,
                 device: dict | None = None) -> Tuple[str, dict]:
    uid = f"spiderfarmer_{device_id}_{path}_{suffix}"
    payload = {
        "name": name,
        "unique_id": uid,
        "state_topic": f"spiderfarmer/{device_id}/state/{path}/{suffix}",
        "command_topic": f"spiderfarmer/{device_id}/command/{path}/{suffix}/set",
        "availability_topic": f"spiderfarmer/{device_id}/availability",
        "min": min_val,
        "max": max_val,
        "step": step,
        "entity_category": "config",
        "device": device or _device_info(device_id, cfg),
    }
    if unit:
        payload["unit_of_measurement"] = unit
    return f"homeassistant/number/{uid}/config", payload


def _text_path(device_id: str, path: str, suffix: str, name: str, pattern: str,
               cfg: dict, device: dict | None = None) -> Tuple[str, dict]:
    uid = f"spiderfarmer_{device_id}_{path}_{suffix}"
    payload = {
        "name": name,
        "unique_id": uid,
        "state_topic": f"spiderfarmer/{device_id}/state/{path}/{suffix}",
        "command_topic": f"spiderfarmer/{device_id}/command/{path}/{suffix}/set",
        "availability_topic": f"spiderfarmer/{device_id}/availability",
        "pattern": pattern,
        "entity_category": "config",
        "device": device or _device_info(device_id, cfg),
    }
    return f"homeassistant/text/{uid}/config", payload


def _switch_path(device_id: str, path: str, suffix: str, name: str, cfg: dict,
                 device: dict | None = None) -> Tuple[str, dict]:
    uid = f"spiderfarmer_{device_id}_{path}_{suffix}"
    payload = {
        "name": name,
        "unique_id": uid,
        "state_topic": f"spiderfarmer/{device_id}/state/{path}/{suffix}",
        "command_topic": f"spiderfarmer/{device_id}/command/{path}/{suffix}/set",
        "availability_topic": f"spiderfarmer/{device_id}/availability",
        "payload_on": "ON",
        "payload_off": "OFF",
        "device": device or _device_info(device_id, cfg),
    }
    return f"homeassistant/switch/{uid}/config", payload


def _switch_path_aliased(device_id: str, path: str, suffix: str, alias: str,
                         name: str, cfg: dict,
                         device: dict | None = None) -> Tuple[str, dict]:
    """Switch counterpart of _number_path_aliased — same wire topics,
    distinct unique_id, so one controller field can appear under multiple
    sub-devices (e.g. natural_wind under Schedule + Cycle + Environment)."""
    uid = f"spiderfarmer_{device_id}_{path}_{suffix}_{alias}"
    payload = {
        "name": name,
        "unique_id": uid,
        "state_topic": f"spiderfarmer/{device_id}/state/{path}/{suffix}",
        "command_topic": f"spiderfarmer/{device_id}/command/{path}/{suffix}/set",
        "availability_topic": f"spiderfarmer/{device_id}/availability",
        "payload_on": "ON",
        "payload_off": "OFF",
        "device": device or _device_info(device_id, cfg),
    }
    return f"homeassistant/switch/{uid}/config", payload


def _select_path(device_id: str, path: str, suffix: str, name: str,
                 options: list, cfg: dict,
                 device: dict | None = None) -> Tuple[str, dict]:
    """HA select entity. Reads label from state topic, writes label to
    command topic; the command_handler maps the label back to the
    underlying controller field."""
    uid = f"spiderfarmer_{device_id}_{path}_{suffix}"
    payload = {
        "name": name,
        "unique_id": uid,
        "state_topic": f"spiderfarmer/{device_id}/state/{path}/{suffix}",
        "command_topic": f"spiderfarmer/{device_id}/command/{path}/{suffix}/set",
        "availability_topic": f"spiderfarmer/{device_id}/availability",
        "options": list(options),
        "entity_category": "config",
        "device": device or _device_info(device_id, cfg),
    }
    return f"homeassistant/select/{uid}/config", payload


def _number_path_aliased(device_id: str, path: str, suffix: str, alias: str,
                         name: str, min_val, max_val, step, cfg: dict,
                         unit: str | None = None,
                         device: dict | None = None) -> Tuple[str, dict]:
    """Like _number_path but lets the unique_id diverge from the topic. Used
    to expose the same temperature-protection fields under two sub-devices
    (Schedule and PPFD) — both control the same controller field, so the
    state and command topics match, but HA needs distinct unique_ids."""
    uid = f"spiderfarmer_{device_id}_{path}_{suffix}_{alias}"
    payload = {
        "name": name,
        "unique_id": uid,
        "state_topic": f"spiderfarmer/{device_id}/state/{path}/{suffix}",
        "command_topic": f"spiderfarmer/{device_id}/command/{path}/{suffix}/set",
        "availability_topic": f"spiderfarmer/{device_id}/availability",
        "min": min_val,
        "max": max_val,
        "step": step,
        "entity_category": "config",
        "device": device or _device_info(device_id, cfg),
    }
    if unit:
        payload["unit_of_measurement"] = unit
    return f"homeassistant/number/{uid}/config", payload


def _settings_subdevice(parent_id: str, parent_name: str, slug: str,
                        suffix_name: str, model: str) -> dict:
    """HA MQTT device-info for a settings sub-device, linked to the main
    controller via via_device so HA renders it as a separate card on the
    parent's device page."""
    return {
        "identifiers": [f"{parent_id}_{slug}"],
        "name": f"{parent_name} {suffix_name}",
        "manufacturer": "Spider Farmer",
        "model": model,
        "via_device": parent_id,
    }


def _light(device_id: str, module: str, name: str, cfg: dict) -> Tuple[str, dict]:
    uid = f"spiderfarmer_{device_id}_{module}"
    base = f"spiderfarmer/{device_id}"
    payload = {
        "name": name,
        "unique_id": uid,
        "schema": "json",
        "state_topic": f"{base}/state/{module}",
        "command_topic": f"{base}/command/{module}/set",
        "brightness": True,
        "brightness_scale": 100,
        "effect": True,
        "effect_list": ["Manual", "Schedule", "PPFD"],
        "availability_topic": f"{base}/availability",
        "device": _device_info(device_id, cfg),
    }
    return f"homeassistant/light/{uid}/config", payload


_FAN_PRESET_MODES = [
    "Manual",
    "Schedule",
    "Cycle",
    "Environment: Prioritize temperature",
    "Environment: Prioritize humidity",
    "Environment: Temperature only",
    "Environment: Humidity only",
    "Environment: Temperature & humidity",
]


# Subset of preset modes for the Environment Mode sub-device dropdown —
# matches the SF App's "Umweltmodus → Betriebsmodus" tab where you pick
# between the 5 environment variants in one place.
_FAN_ENV_SUBMODES = [
    "Prioritize temperature",
    "Prioritize humidity",
    "Temperature only",
    "Humidity only",
    "Temperature & humidity",
]


def _fan(device_id: str, module: str, name: str, speed_max: int, cfg: dict,
         oscillation: bool = False, preset_modes: bool = False) -> Tuple[str, dict]:
    uid = f"spiderfarmer_{device_id}_{module}"
    base = f"spiderfarmer/{device_id}"
    payload = {
        "name": name,
        "unique_id": uid,
        "state_topic": f"{base}/state/{module}",
        "state_value_template": "{{ value_json.state }}",
        "command_topic": f"{base}/command/{module}/set",
        "payload_on": "ON",
        "payload_off": "OFF",
        "percentage_state_topic": f"{base}/state/{module}",
        "percentage_value_template": "{{ value_json.percentage | int }}",
        "percentage_command_topic": f"{base}/command/{module}/percentage/set",
        "speed_range_min": 1,
        "speed_range_max": speed_max,
        "availability_topic": f"{base}/availability",
        "device": _device_info(device_id, cfg),
    }
    if oscillation:
        payload.update({
            "oscillation_state_topic": f"{base}/state/{module}",
            "oscillation_value_template": "{{ 'oscillate_on' if value_json.oscillating else 'oscillate_off' }}",
            "oscillation_command_topic": f"{base}/command/{module}/oscillation/set",
            "payload_oscillation_on": "oscillate_on",
            "payload_oscillation_off": "oscillate_off",
        })
    if preset_modes:
        # Mirror the SF App's Modus dropdown — 8 modes including 5 Umwelt
        # variants. Selection routes back via /command/{module}/preset_mode/set
        # and resolves to the matching modeType in command_handler.
        payload.update({
            "preset_mode_state_topic": f"{base}/state/{module}/mode_label",
            "preset_mode_command_topic": f"{base}/command/{module}/preset_mode/set",
            "preset_modes": list(_FAN_PRESET_MODES),
        })
    return f"homeassistant/fan/{uid}/config", payload


def _light_extras(device_id: str, module: str, friendly: str, cfg: dict) -> list:
    """Sub-device entities mirroring the SF App's "Lampe Einstellungen" screen
    for one light. Two sub-devices linked via via_device:
      - Schedule Mode: schedule_brightness, schedule_start/end, fade_minutes,
        plus the Temperaturschutz fields (dim/off thresholds).
      - PPFD Mode: ppfd_target/min/max/start/end/fade_minutes, plus the same
        Temperaturschutz fields (per user request — Temperaturschutz applies
        in both modes, so it is exposed in both groups rather than a
        separate settings card).
    Note: dim_threshold/off_threshold appear under each sub-device with
    distinct unique_ids but identical state/command topics, so HA shows
    them in both cards while a single change keeps them synchronized.
    Sub-device names are prefixed with the controller's friendly_name
    so HA generates entity_ids that match the main device's prefix."""
    parent_id = f"spiderfarmer_{device_id}"
    full_name = f"{cfg.get('friendly_name', 'GGS')} {friendly}"
    sched_dev = _settings_subdevice(parent_id, full_name, f"{module}_schedule",
                                    "Schedule Mode", "Schedule settings")
    ppfd_dev = _settings_subdevice(parent_id, full_name, f"{module}_ppfd",
                                   "PPFD Mode", "PPFD settings")
    HHMM = r"^([01]\d|2[0-3]):[0-5]\d$"
    return [
        # Schedule Mode
        _number_path(device_id, module, "schedule_brightness",
                     "Brightness", 0, 100, 1, cfg, unit="%", device=sched_dev),
        _text_path(device_id, module, "schedule_start",
                   "Start Time", HHMM, cfg, device=sched_dev),
        _text_path(device_id, module, "schedule_end",
                   "End Time", HHMM, cfg, device=sched_dev),
        _number_path(device_id, module, "fade_minutes",
                     "Fade Time", 0, 240, 1, cfg, unit="min", device=sched_dev),
        # Temperaturschutz under Schedule
        _number_path_aliased(device_id, module, "dim_threshold", "schedule",
                             "Dim Threshold", 0, 50, 0.1, cfg,
                             unit="°C", device=sched_dev),
        _number_path_aliased(device_id, module, "off_threshold", "schedule",
                             "Off Threshold", 0, 50, 0.1, cfg,
                             unit="°C", device=sched_dev),
        # PPFD Mode
        _number_path(device_id, module, "ppfd_target",
                     "Target PPFD", 0, 1000, 1, cfg,
                     unit="µmol/m²/s", device=ppfd_dev),
        _number_path(device_id, module, "ppfd_min",
                     "Min Brightness", 0, 100, 1, cfg, unit="%", device=ppfd_dev),
        _number_path(device_id, module, "ppfd_max",
                     "Max Brightness", 0, 100, 1, cfg, unit="%", device=ppfd_dev),
        _text_path(device_id, module, "ppfd_start",
                   "Start Time", HHMM, cfg, device=ppfd_dev),
        _text_path(device_id, module, "ppfd_end",
                   "End Time", HHMM, cfg, device=ppfd_dev),
        _number_path(device_id, module, "ppfd_fade_minutes",
                     "Fade Time", 0, 240, 1, cfg, unit="min", device=ppfd_dev),
        # Temperaturschutz under PPFD (same topics, distinct unique_id)
        _number_path_aliased(device_id, module, "dim_threshold", "ppfd",
                             "Dim Threshold", 0, 50, 0.1, cfg,
                             unit="°C", device=ppfd_dev),
        _number_path_aliased(device_id, module, "off_threshold", "ppfd",
                             "Off Threshold", 0, 50, 0.1, cfg,
                             unit="°C", device=ppfd_dev),
    ]


def _fan_extras(device_id: str, module: str, friendly: str, cfg: dict,
                speed_max: int = 10, oscillation: bool = True,
                natural_wind: bool = True) -> list:
    """Sub-device entities mirroring the SF App's fan settings screen
    for one fan/blower. Three sub-devices linked via via_device:
      - Schedule Mode: schedule_start, schedule_end + Speed, Standby Speed
        [+ Oscillation] [+ Natural Wind]
      - Cycle Mode: cycle_start, cycle_run, cycle_off, cycle_times +
        Speed, Standby Speed [+ Oscillation] [+ Natural Wind]
      - Environment Mode: submode dropdown (5 env variants) + Speed,
        Standby Speed [+ Oscillation] [+ Natural Wind]
    Speed / Standby Speed / Oscillation / Natural Wind apply across every
    mode, so they are aliased under each card with distinct unique_ids
    but shared wire topics — toggling any copy keeps the others in sync.
    `speed_max` parameterizes the speed range (10 for Fan Circulation,
    100 for Fan Exhaust/blower). `oscillation=False` skips Oscillation
    (blower has no shaking head). `natural_wind=False` skips Natural Wind
    (blower has no natural-wind feature either)."""
    parent_id = f"spiderfarmer_{device_id}"
    full_name = f"{cfg.get('friendly_name', 'GGS')} {friendly}"
    sched_dev = _settings_subdevice(parent_id, full_name, f"{module}_schedule",
                                    "Schedule Mode", "Schedule settings")
    cycle_dev = _settings_subdevice(parent_id, full_name, f"{module}_cycle",
                                    "Cycle Mode", "Cycle settings")
    env_dev = _settings_subdevice(parent_id, full_name, f"{module}_env",
                                  "Environment Mode", "Environment settings")
    HHMM = r"^([01]\d|2[0-3]):[0-5]\d$"

    def _shared_speed_settings(card_dev: dict, alias: str) -> list:
        """Speed / Standby Speed / Oscillation / Natural Wind aliased under
        each card. Distinct unique_ids per alias, shared wire topics."""
        items = [
            _number_path_aliased(device_id, module, "schedule_speed", alias,
                                 "Speed", 1, speed_max, 1, cfg, device=card_dev),
            _number_path_aliased(device_id, module, "standby_speed", alias,
                                 "Standby Speed", 0, speed_max, 1, cfg,
                                 device=card_dev),
        ]
        if oscillation:
            items.append(
                _number_path_aliased(device_id, module, "oscillation_level",
                                     alias, "Oscillation", 0, 10, 1, cfg,
                                     device=card_dev),
            )
        if natural_wind:
            items.append(
                _switch_path_aliased(device_id, module, "natural_wind", alias,
                                     "Natural Wind", cfg, device=card_dev),
            )
        return items

    return [
        # Schedule Mode
        _text_path(device_id, module, "schedule_start",
                   "Start Time", HHMM, cfg, device=sched_dev),
        _text_path(device_id, module, "schedule_end",
                   "End Time", HHMM, cfg, device=sched_dev),
        *_shared_speed_settings(sched_dev, "schedule"),
        # Cycle Mode
        _text_path(device_id, module, "cycle_start",
                   "Start Time", HHMM, cfg, device=cycle_dev),
        _number_path(device_id, module, "cycle_run_minutes",
                     "Run Time", 0, 1440, 1, cfg, unit="min", device=cycle_dev),
        _number_path(device_id, module, "cycle_off_minutes",
                     "Off Time", 0, 1440, 1, cfg, unit="min", device=cycle_dev),
        _number_path(device_id, module, "cycle_times",
                     "Cycles", 1, 100, 1, cfg, device=cycle_dev),
        *_shared_speed_settings(cycle_dev, "cycle"),
        # Environment Mode
        _select_path(device_id, module, "env_submode",
                     "Submode", _FAN_ENV_SUBMODES, cfg, device=env_dev),
        *_shared_speed_settings(env_dev, "env"),
    ]


def publish_discovery_for_device(
    client: mqtt.Client, device_id: str, device_cfg: dict
) -> None:
    entities = []

    # Prefixes ensure alphabetical sort matches desired display order:
    # Air → Light → Fan → Soil Avg → Soil Sensors → Switch → Outlet

    # ── Air sensors ───────────────────────────────────────────────────────────
    entities += [
        _sensor(device_id, "temperature", "Air Temperature", "°C",       "temperature", device_cfg),
        _sensor(device_id, "humidity",    "Air Humidity",    "%",        "humidity",    device_cfg),
        _sensor(device_id, "vpd",         "Air VPD",         "kPa",      None,          device_cfg),
        _sensor(device_id, "co2",         "Air CO₂",         "ppm",      "carbon_dioxide", device_cfg),
        _sensor(device_id, "ppfd",        "Air PPFD",        "µmol/m²/s", None,         device_cfg),
    ]

    # ── Light ─────────────────────────────────────────────────────────────────
    # Light 1 gets the new app-parity entities (Schedule Mode + PPFD Mode
    # sub-devices). Light 2 stays as the simple variant — only Light 1 was
    # exposed via the SF App's settings screen the user mirrored.
    entities.append(_light(device_id, "light",  "Light 1", device_cfg))
    entities += _light_extras(device_id, "light", "Light 1", device_cfg)
    entities.append(_light(device_id, "light2", "Light 2", device_cfg))

    # ── Fans ──────────────────────────────────────────────────────────────────
    # Fan Circulation: oscillating tent fan (speed 1-10, has shake head and
    # natural-wind feature). Fan Exhaust/blower: extraction fan (speed
    # 1-100, no oscillation, no natural-wind). Both get the same preset
    # mode dropdown and the same four settings sub-devices, just with
    # speed range and the irrelevant entities suppressed for the blower.
    entities.append(_fan(device_id, "fan", "Fan Circulation", 10, device_cfg,
                         preset_modes=True))
    entities += _fan_extras(device_id, "fan", "Fan", device_cfg,
                            speed_max=10)
    entities.append(_fan(device_id, "blower", "Fan Exhaust", 100, device_cfg,
                         preset_modes=True))
    entities += _fan_extras(device_id, "blower", "Fan Exhaust", device_cfg,
                            speed_max=100, oscillation=False,
                            natural_wind=False)

    # ── Soil sensors (average) ────────────────────────────────────────────────
    entities += [
        _sensor(device_id, "temp_soil", "Soil Avg Temperature", "°C",    "temperature", device_cfg),
        _sensor(device_id, "humi_soil", "Soil Avg Humidity",    "%",     "humidity",    device_cfg),
        _sensor(device_id, "ec_soil",   "Soil Avg EC",          "mS/cm", None,          device_cfg),
    ]

    # Individual soil sensors published dynamically by proxy on first detection

    # ── Accessories ───────────────────────────────────────────────────────────
    entities += [
        _switch(device_id, "heater",       "Switch Heater",       device_cfg),
        _switch(device_id, "humidifier",   "Switch Humidifier",   device_cfg),
        _switch(device_id, "dehumidifier", "Switch Dehumidifier", device_cfg),
    ]

    # ── Outlets ───────────────────────────────────────────────────────────────
    num_outlets = device_cfg.get("outlets", 10)
    for i in range(1, num_outlets + 1):
        entities.append(_switch(device_id, f"outlet_{i}", f"Outlet {i}", device_cfg))

    for topic, payload in entities:
        client.publish(topic, json.dumps(payload), retain=True)
        logger.debug("Discovery published: %s", topic)


def unpublish_outlet_discovery(
    client: mqtt.Client, device_id: str, outlet_num: int
) -> None:
    """Remove an outlet entity from HA by publishing an empty retained payload
    to its discovery topic. Used by the proxy when it learns the controller
    has fewer outlets than the static discovery published (e.g. PS5 has 5,
    static publishes 10)."""
    uid = f"spiderfarmer_{device_id}_outlet_{outlet_num}"
    client.publish(f"homeassistant/switch/{uid}/config", "", retain=True)


def publish_soil_sensor_discovery(
    client: mqtt.Client, device_id: str, sensor_id: str, device_cfg: dict
) -> None:
    """Dynamically publish HA discovery for one soil sensor using its hardware ID."""
    short_id = sensor_id[-8:].upper()
    dev = _device_info(device_id, device_cfg)
    for sf, name, unit, dc in [
        ("temp", f"Soil Sensor {short_id} Temperature", "°C",    "temperature"),
        ("humi", f"Soil Sensor {short_id} Humidity",    "%",     "humidity"),
        ("ec",   f"Soil Sensor {short_id} EC",          "mS/cm", None),
    ]:
        uid = f"spiderfarmer_{device_id}_soil_{sensor_id}_{sf}"
        payload: dict = {
            "name": name,
            "unique_id": uid,
            "state_topic": f"spiderfarmer/{device_id}/state/soil_{sensor_id}_{sf}",
            "availability_topic": f"spiderfarmer/{device_id}/availability",
            "state_class": "measurement",
            "unit_of_measurement": unit,
            "device": dev,
        }
        if dc:
            payload["device_class"] = dc
        client.publish(f"homeassistant/sensor/{uid}/config", json.dumps(payload), retain=True)
    logger.info("Soil sensor discovery published: %s (%s)", short_id, sensor_id)
