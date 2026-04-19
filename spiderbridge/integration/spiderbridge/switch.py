import logging
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN
from .coordinator import MQTTCoordinator

_LOGGER = logging.getLogger(__name__)

SWITCHES = [
    ("heater",       "Switch Heater"),
    ("humidifier",   "Switch Humidifier"),
    ("dehumidifier", "Switch Dehumidifier"),
] + [(f"outlet_{i}", f"Outlet {i}") for i in range(1, 11)]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: MQTTCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        SpiderFarmerSwitch(coordinator, field, name)
        for field, name in SWITCHES
    ])


class SpiderFarmerSwitch(SwitchEntity):
    _attr_should_poll = False

    def __init__(self, coordinator: MQTTCoordinator, field: str, name: str):
        self._coordinator = coordinator
        self._field = field
        self._attr_name = name
        self._attr_unique_id = f"spiderfarmer_{coordinator.device_id}_{field}"
        self._attr_is_on = None
        self._attr_available = False

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._coordinator.device_id)},
            name="Spider Farmer GGS",
            manufacturer="Spider Farmer",
            model="GGS Controller",
        )

    async def async_added_to_hass(self) -> None:
        self._coordinator.subscribe_state(self._field, self._on_state)
        self._coordinator.subscribe_availability(self._on_availability)

    def _on_state(self, payload: str) -> None:
        self._attr_is_on = payload == "ON"
        self.async_write_ha_state()

    def _on_availability(self, available: bool) -> None:
        self._attr_available = available
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs) -> None:
        self._coordinator.publish(
            f"spiderfarmer/{self._coordinator.device_id}/command/{self._field}/set",
            "ON",
        )

    async def async_turn_off(self, **kwargs) -> None:
        self._coordinator.publish(
            f"spiderfarmer/{self._coordinator.device_id}/command/{self._field}/set",
            "OFF",
        )
