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


def _fan(device_id: str, module: str, name: str, speed_max: int, cfg: dict,
         oscillation: bool = False) -> Tuple[str, dict]:
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
    return f"homeassistant/fan/{uid}/config", payload


def publish_discovery_for_device(
    client: mqtt.Client, device_id: str, device_cfg: dict
) -> None:
    entities = []

    # Prefixes ensure alphabetical sort matches desired display order:
    # Air → Light → Fan → Soil Avg → Soil Sensors → Switch → Outlet

    # ── Air sensors ───────────────────────────────────────────────────────────
    entities += [
        _sensor(device_id, "temperature", "Air Temperature", "°C",  "temperature", device_cfg),
        _sensor(device_id, "humidity",    "Air Humidity",    "%",   "humidity",    device_cfg),
        _sensor(device_id, "vpd",         "Air VPD",         "kPa", None,          device_cfg),
    ]

    # ── Light ─────────────────────────────────────────────────────────────────
    entities.append(_light(device_id, "light",  "Light 1", device_cfg))
    entities.append(_light(device_id, "light2", "Light 2", device_cfg))

    # ── Fans ──────────────────────────────────────────────────────────────────
    entities.append(_fan(device_id, "blower", "Fan Exhaust",     100, device_cfg))
    entities.append(_fan(device_id, "fan", "Fan Circulation", 10, device_cfg))

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
