DOMAIN = "spiderbridge"
BROKER = "127.0.0.1"
PORT = 1883
DEFAULT_DEVICE_ID = "ggs_1"
DEVICES_YAML = "/data/devices.yaml"

from homeassistant.helpers.entity import DeviceInfo  # noqa: E402


def device_info(device_id: str) -> DeviceInfo:
    return DeviceInfo(
        identifiers={("spiderbridge", device_id)},
        name="Spider Farmer GGS",
        manufacturer="Spider Farmer",
        model="GGS Controller",
    )
