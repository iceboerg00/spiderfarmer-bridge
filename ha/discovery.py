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
        "effect_list": ["Modus: Manual / Timer", "Modus: PPFD"],
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


def _fan_extras(device_id: str, module: str, friendly: str, cfg: dict) -> list:
    """Sub-device entities mirroring the SF App's Lüfter-Einstellungen screen
    for one fan/blower. Three sub-devices linked via via_device:
      - Zeitfenstermodus: schedule_start, schedule_end
      - Zyklusmodus: cycle_start, cycle_run, cycle_off, cycle_times
      - Geschwindigkeiten: schedule_speed, standby_speed, oscillation_level
    Plus a switch on the main device for natural_wind."""
    parent_id = f"spiderfarmer_{device_id}"
    sched_dev = _settings_subdevice(parent_id, friendly, f"{module}_schedule",
                                    "Schedule Mode", "Schedule settings")
    cycle_dev = _settings_subdevice(parent_id, friendly, f"{module}_cycle",
                                    "Cycle Mode", "Cycle settings")
    speeds_dev = _settings_subdevice(parent_id, friendly, f"{module}_speeds",
                                     "Speeds", "Speed settings")
    HHMM = r"^([01]\d|2[0-3]):[0-5]\d$"
    return [
        # Schedule Mode
        _text_path(device_id, module, "schedule_start",
                   "Start Time", HHMM, cfg, device=sched_dev),
        _text_path(device_id, module, "schedule_end",
                   "End Time", HHMM, cfg, device=sched_dev),
        # Cycle Mode
        _text_path(device_id, module, "cycle_start",
                   "Start Time", HHMM, cfg, device=cycle_dev),
        _number_path(device_id, module, "cycle_run_minutes",
                     "Run Time", 0, 1440, 1, cfg, unit="min", device=cycle_dev),
        _number_path(device_id, module, "cycle_off_minutes",
                     "Off Time", 0, 1440, 1, cfg, unit="min", device=cycle_dev),
        _number_path(device_id, module, "cycle_times",
                     "Cycles", 1, 100, 1, cfg, device=cycle_dev),
        # Speeds
        _number_path(device_id, module, "schedule_speed",
                     "Speed", 1, 10, 1, cfg, device=speeds_dev),
        _number_path(device_id, module, "standby_speed",
                     "Standby Speed", 0, 10, 1, cfg, device=speeds_dev),
        _number_path(device_id, module, "oscillation_level",
                     "Oscillation", 0, 10, 1, cfg, device=speeds_dev),
        # Natural wind sits on the main device.
        _switch_path(device_id, module, "natural_wind",
                     f"{friendly} Natural Wind", cfg),
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
    entities.append(_light(device_id, "light",  "Light 1", device_cfg))
    entities.append(_light(device_id, "light2", "Light 2", device_cfg))

    # ── Fans ──────────────────────────────────────────────────────────────────
    entities.append(_fan(device_id, "blower", "Fan Exhaust", 100, device_cfg))
    # Fan Circulation gets the new app-parity entities: preset_modes on the
    # main fan plus three sub-devices (Schedule Mode, Cycle Mode, Speeds)
    # and a switch for natural wind. Fan Exhaust (blower) is intentionally
    # left as the simple variant for now — same pattern, follow-up.
    entities.append(_fan(device_id, "fan", "Fan Circulation", 10, device_cfg,
                         preset_modes=True))
    entities += _fan_extras(device_id, "fan", "Fan", device_cfg)

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
