import logging
import yaml
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, DEFAULT_DEVICE_ID, DEVICES_YAML
from .coordinator import MQTTCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "switch", "fan", "light"]


def _get_device_id() -> str:
    p = Path(DEVICES_YAML)
    if p.exists():
        try:
            with open(p) as f:
                devices = yaml.safe_load(f) or []
                if devices:
                    return devices[0]["id"]
        except Exception as e:
            _LOGGER.warning("Could not read devices.yaml: %s", e)
    return DEFAULT_DEVICE_ID


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    device_id = await hass.async_add_executor_job(_get_device_id)
    _LOGGER.info("Setting up SpiderBridge for device_id=%s", device_id)

    coordinator = MQTTCoordinator(hass, device_id)
    connected = await hass.async_add_executor_job(coordinator.start)
    if not connected:
        return False

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: MQTTCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        coordinator.stop()
    return unload_ok
