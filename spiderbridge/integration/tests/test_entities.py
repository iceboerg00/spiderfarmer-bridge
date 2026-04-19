import sys
import os
import json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import MagicMock, patch

# --- HA stub setup (allows tests to run without homeassistant installed) ---
class _StubEntity:
    def async_write_ha_state(self): pass

_ha_stubs = {
    'homeassistant':                         MagicMock(),
    'homeassistant.components':              MagicMock(),
    'homeassistant.components.sensor':       MagicMock(SensorEntity=_StubEntity, SensorDeviceClass=MagicMock(), SensorStateClass=MagicMock()),
    'homeassistant.components.switch':       MagicMock(SwitchEntity=_StubEntity),
    'homeassistant.components.fan':          MagicMock(FanEntity=_StubEntity, FanEntityFeature=MagicMock()),
    'homeassistant.components.light':        MagicMock(LightEntity=_StubEntity, LightEntityFeature=MagicMock(), ColorMode=MagicMock()),
    'homeassistant.config_entries':          MagicMock(),
    'homeassistant.core':                    MagicMock(),
    'homeassistant.helpers':                 MagicMock(),
    'homeassistant.helpers.entity':          MagicMock(DeviceInfo=dict),
    'homeassistant.helpers.entity_platform': MagicMock(),
}
for mod, stub in _ha_stubs.items():
    sys.modules[mod] = stub
# --- end HA stub setup ---

from spiderbridge.coordinator import MQTTCoordinator
from spiderbridge.sensor import SpiderFarmerSensor
from spiderbridge.switch import SpiderFarmerSwitch
from spiderbridge.fan import SpiderFarmerFan
from spiderbridge.light import SpiderFarmerLight


def _make_coordinator(device_id="ggs_1"):
    hass = MagicMock()
    hass.loop = MagicMock()
    hass.loop.call_soon_threadsafe.side_effect = lambda fn, *args: fn(*args)
    with patch("spiderbridge.coordinator.mqtt.Client") as mock_client_cls:
        mock_client_cls.return_value = MagicMock()
        return MQTTCoordinator(hass, device_id)


def test_sensor_parses_float_payload():
    coord = _make_coordinator()
    sensor = SpiderFarmerSensor(coord, "temperature", "Air Temperature", "°C", None)
    sensor._on_state("22.5")
    assert sensor._attr_native_value == 22.5


def test_sensor_parses_string_payload():
    coord = _make_coordinator()
    sensor = SpiderFarmerSensor(coord, "vpd", "VPD", "kPa", None)
    sensor._on_state("not_a_number")
    assert sensor._attr_native_value == "not_a_number"


def test_sensor_availability_true():
    coord = _make_coordinator()
    sensor = SpiderFarmerSensor(coord, "temperature", "Air Temperature", "°C", None)
    sensor._on_availability(True)
    assert sensor._attr_available is True


def test_sensor_availability_false():
    coord = _make_coordinator()
    sensor = SpiderFarmerSensor(coord, "temperature", "Air Temperature", "°C", None)
    sensor._on_availability(False)
    assert sensor._attr_available is False


def test_switch_on_payload():
    coord = _make_coordinator()
    sw = SpiderFarmerSwitch(coord, "heater", "Heater")
    sw._on_state("ON")
    assert sw._attr_is_on is True


def test_switch_off_payload():
    coord = _make_coordinator()
    sw = SpiderFarmerSwitch(coord, "heater", "Heater")
    sw._on_state("OFF")
    assert sw._attr_is_on is False


def test_fan_percentage_conversion_blower():
    coord = _make_coordinator()
    fan = SpiderFarmerFan(coord, "blower", "Fan Exhaust", 100)
    fan._on_state(json.dumps({"state": "ON", "percentage": 50}))
    assert fan._attr_percentage == 50  # 50/100 * 100 = 50%


def test_fan_percentage_conversion_circulation():
    coord = _make_coordinator()
    fan = SpiderFarmerFan(coord, "fan", "Fan Circulation", 10)
    fan._on_state(json.dumps({"state": "ON", "percentage": 5}))
    assert fan._attr_percentage == 50  # 5/10 * 100 = 50%


def test_light_brightness_conversion():
    coord = _make_coordinator()
    light = SpiderFarmerLight(coord, "light", "Light 1")
    light._on_state(json.dumps({"state": "ON", "brightness": 100, "effect": "Modus: Manual / Timer"}))
    assert light._attr_brightness == 255  # round(100/100 * 255) = 255


def test_light_brightness_half():
    coord = _make_coordinator()
    light = SpiderFarmerLight(coord, "light", "Light 1")
    light._on_state(json.dumps({"state": "ON", "brightness": 50, "effect": "Modus: Manual / Timer"}))
    assert light._attr_brightness == 127  # round(50/100 * 255) = 127


def test_light_off_state():
    coord = _make_coordinator()
    light = SpiderFarmerLight(coord, "light", "Light 1")
    light._on_state(json.dumps({"state": "OFF", "brightness": 0, "effect": "Modus: Manual / Timer"}))
    assert light._attr_is_on is False
