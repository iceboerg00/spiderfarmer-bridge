import json
import logging
import math
from homeassistant.components.light import LightEntity, LightEntityFeature, ColorMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN
from .coordinator import MQTTCoordinator

_LOGGER = logging.getLogger(__name__)

LIGHTS = [
    ("light",  "Light 1"),
    ("light2", "Light 2"),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: MQTTCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        SpiderFarmerLight(coordinator, field, name)
        for field, name in LIGHTS
    ])


class SpiderFarmerLight(LightEntity):
    _attr_should_poll = False
    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}
    _attr_supported_features = LightEntityFeature.EFFECT
    _attr_effect_list = ["Modus: Manual / Timer", "Modus: PPFD"]

    def __init__(self, coordinator: MQTTCoordinator, field: str, name: str):
        self._coordinator = coordinator
        self._field = field
        self._attr_name = name
        self._attr_unique_id = f"spiderfarmer_{coordinator.device_id}_{field}"
        self._attr_is_on = None
        self._attr_brightness = None
        self._attr_effect = None
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
            level = data.get("brightness", 0)
            self._attr_brightness = math.floor(level / 100 * 255)
            self._attr_effect = data.get("effect")
        except (json.JSONDecodeError, TypeError):
            pass
        self.async_write_ha_state()

    def _on_availability(self, available: bool) -> None:
        self._attr_available = available
        self.async_write_ha_state()

    async def async_turn_on(self, brightness=None, effect=None, **kwargs) -> None:
        payload: dict = {"state": "ON"}
        if brightness is not None:
            payload["brightness"] = round(brightness / 255 * 100)
        if effect is not None:
            payload["effect"] = effect
        self._coordinator.publish(
            f"spiderfarmer/{self._coordinator.device_id}/command/{self._field}/set",
            json.dumps(payload),
        )

    async def async_turn_off(self, **kwargs) -> None:
        self._coordinator.publish(
            f"spiderfarmer/{self._coordinator.device_id}/command/{self._field}/set",
            json.dumps({"state": "OFF"}),
        )
