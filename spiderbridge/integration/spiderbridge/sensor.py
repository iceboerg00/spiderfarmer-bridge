import logging
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .const import DOMAIN, device_info as _device_info
from .coordinator import MQTTCoordinator

_LOGGER = logging.getLogger(__name__)

STATIC_SENSORS = [
    ("temperature", "Air Temperature", "°C",    SensorDeviceClass.TEMPERATURE),
    ("humidity",    "Air Humidity",    "%",     SensorDeviceClass.HUMIDITY),
    ("vpd",         "Air VPD",         "kPa",   None),
    ("temp_soil",   "Soil Avg Temperature", "°C",    SensorDeviceClass.TEMPERATURE),
    ("humi_soil",   "Soil Avg Humidity",    "%",     SensorDeviceClass.HUMIDITY),
    ("ec_soil",     "Soil Avg EC",          "mS/cm", None),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: MQTTCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        SpiderFarmerSensor(coordinator, field, name, unit, device_class)
        for field, name, unit, device_class in STATIC_SENSORS
    ])

    seen_soil: set[str] = set()

    def on_soil(suffix: str, payload: str) -> None:
        # suffix: soil_<sensor_id>_<field>  e.g. soil_3839383705306F29_temp
        parts = suffix.split("_")
        if len(parts) < 3:
            return
        sensor_id = parts[1]
        sf = parts[2]
        key = f"{sensor_id}_{sf}"
        if key in seen_soil:
            return
        seen_soil.add(key)
        short = sensor_id[-8:].upper()
        name_map = {
            "temp": f"Soil {short} Temperature",
            "humi": f"Soil {short} Humidity",
            "ec":   f"Soil {short} EC",
        }
        unit_map = {"temp": "°C", "humi": "%", "ec": "mS/cm"}
        dc_map = {
            "temp": SensorDeviceClass.TEMPERATURE,
            "humi": SensorDeviceClass.HUMIDITY,
            "ec":   None,
        }
        entity = SpiderFarmerSensor(
            coordinator, suffix,
            name_map.get(sf, suffix),
            unit_map.get(sf, ""),
            dc_map.get(sf),
        )
        async_add_entities([entity])

    coordinator.subscribe_soil(on_soil)


class SpiderFarmerSensor(SensorEntity):
    _attr_should_poll = False
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: MQTTCoordinator,
        field: str,
        name: str,
        unit: str,
        device_class,
    ):
        self._coordinator = coordinator
        self._field = field
        self._attr_name = name
        self._attr_unique_id = f"spiderfarmer_{coordinator.device_id}_{field}"
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_native_value = None
        self._attr_available = False

    @property
    def device_info(self):
        return _device_info(self._coordinator.device_id)

    async def async_added_to_hass(self) -> None:
        self._coordinator.subscribe_state(self._field, self._on_state)
        self._coordinator.subscribe_availability(self._on_availability)

    def _on_state(self, payload: str) -> None:
        try:
            self._attr_native_value = float(payload)
        except ValueError:
            self._attr_native_value = payload
        self.async_write_ha_state()

    def _on_availability(self, available: bool) -> None:
        self._attr_available = available
        self.async_write_ha_state()
