import logging
import time

import paho.mqtt.client as mqtt

from .discovery import publish_discovery_for_device

logger = logging.getLogger(__name__)


class DiscoveryPublisher:
    """Subscribes to availability topics, publishes HA discovery on first 'online'."""

    def __init__(self, config: dict, mqtt_client: mqtt.Client):
        self.config = config
        self.mqtt_client = mqtt_client
        self._published: set = set()

    def start(self) -> None:
        self.mqtt_client.on_message = self._on_message
        self.mqtt_client.subscribe("spiderfarmer/+/availability")
        # Publish immediately for known devices (retained topics may already be online)
        for device in self.config.get("devices", []):
            self._publish_for_device(device["id"], device)
        logger.info("Discovery publisher started, monitoring availability topics")

    def _on_message(self, client, userdata, message) -> None:
        if message.payload.decode() != "online":
            return
        parts = message.topic.split("/")
        if len(parts) < 3:
            return
        device_id = parts[1]
        if device_id in self._published:
            return
        device_cfg = self._find_device(device_id)
        if device_cfg is None:
            logger.warning("online received for unknown device_id=%s", device_id)
            return
        self._publish_for_device(device_id, device_cfg)

    def _publish_for_device(self, device_id: str, device_cfg: dict) -> None:
        publish_discovery_for_device(self.mqtt_client, device_id, device_cfg)
        self._published.add(device_id)
        logger.info("HA discovery published for %s", device_id)

    def _find_device(self, device_id: str):
        for d in self.config.get("devices", []):
            if d["id"] == device_id:
                return d
        return None
