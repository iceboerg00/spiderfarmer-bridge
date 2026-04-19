import json
import logging
from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN
from .coordinator import MQTTCoordinator

_LOGGER = logging.getLogger(__name__)

FANS = [
    ("blower", "Fan Exhaust",     100),
    ("fan",    "Fan Circulation",  10),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: MQTTCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        SpiderFarmerFan(coordinator, field, name, max_speed)
        for field, name, max_speed in FANS
    ])


class SpiderFarmerFan(FanEntity):
    _attr_should_poll = False
    _attr_supported_features = FanEntityFeature.SET_SPEED

    def __init__(self, coordinator: MQTTCoordinator, field: str, name: str, max_speed: int):
        self._coordinator = coordinator
        self._field = field
        self._max_speed = max_speed
        self._attr_name = name
        self._attr_unique_id = f"spiderfarmer_{coordinator.device_id}_{field}"
        self._attr_is_on = None
        self._attr_percentage = None
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
        try:
            data = json.loads(payload)
            self._attr_is_on = data.get("state") == "ON"
            raw = data.get("percentage", 0)
            self._attr_percentage = int(raw / self._max_speed * 100) if self._max_speed else 0
        except (json.JSONDecodeError, TypeError, ZeroDivisionError):
            pass
        self.async_write_ha_state()

    def _on_availability(self, available: bool) -> None:
        self._attr_available = available
        self.async_write_ha_state()

    async def async_turn_on(self, percentage=None, **kwargs) -> None:
        if percentage is not None:
            await self.async_set_percentage(percentage)
        else:
            self._coordinator.publish(
                f"spiderfarmer/{self._coordinator.device_id}/command/{self._field}/set",
                "ON",
            )

    async def async_turn_off(self, **kwargs) -> None:
        self._coordinator.publish(
            f"spiderfarmer/{self._coordinator.device_id}/command/{self._field}/set",
            "OFF",
        )

    async def async_set_percentage(self, percentage: int) -> None:
        level = round(percentage / 100 * self._max_speed)
        self._coordinator.publish(
            f"spiderfarmer/{self._coordinator.device_id}/command/{self._field}/percentage/set",
            str(level),
        )
