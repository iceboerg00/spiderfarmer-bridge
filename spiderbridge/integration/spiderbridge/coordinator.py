import logging
from collections import defaultdict
from typing import Callable

import paho.mqtt.client as mqtt

from .const import BROKER, PORT

_LOGGER = logging.getLogger(__name__)


class MQTTCoordinator:
    def __init__(self, hass, device_id: str):
        self.hass = hass
        self.device_id = device_id
        try:
            self._client = mqtt.Client(
                mqtt.CallbackAPIVersion.VERSION1,
                client_id=f"ha-spiderbridge-{device_id}",
            )
        except AttributeError:
            # paho-mqtt < 2.0 fallback
            self._client = mqtt.Client(client_id=f"ha-spiderbridge-{device_id}")
        self._listeners: dict[str, list[Callable]] = defaultdict(list)
        self._availability_listeners: list[Callable] = []
        self._soil_listeners: list[Callable] = []
        self._started: bool = False

    def _on_connect(self, client, userdata, flags, rc) -> None:
        if rc == 0:
            client.subscribe(f"spiderfarmer/{self.device_id}/state/#")
            client.subscribe(f"spiderfarmer/{self.device_id}/availability")
            _LOGGER.info("Subscribed to MQTT topics for %s", self.device_id)
        else:
            _LOGGER.error("MQTT connect failed with code %s", rc)

    def start(self) -> bool:
        try:
            self._client.on_message = self._on_message
            self._client.on_connect = self._on_connect
            self._client.connect(BROKER, PORT, keepalive=60)
            self._client.subscribe(f"spiderfarmer/{self.device_id}/state/#")
            self._client.subscribe(f"spiderfarmer/{self.device_id}/availability")
            self._client.loop_start()
            _LOGGER.info("Connected to MQTT broker at %s:%s", BROKER, PORT)
            self._started = True
            return True
        except Exception as e:
            _LOGGER.error("Failed to connect to MQTT broker: %s", e)
            return False

    def _on_message(self, client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode("utf-8", errors="replace")
        self.hass.loop.call_soon_threadsafe(self._dispatch, topic, payload)

    def _dispatch(self, topic: str, payload: str) -> None:
        """Route an MQTT message to registered callbacks. Always called on the HA event loop."""
        avail_topic = f"spiderfarmer/{self.device_id}/availability"
        state_prefix = f"spiderfarmer/{self.device_id}/state/"

        if topic == avail_topic:
            available = payload == "online"
            for cb in self._availability_listeners:
                cb(available)
            return

        if not topic.startswith(state_prefix):
            return

        suffix = topic[len(state_prefix):]

        if suffix.startswith("soil_"):
            for cb in self._soil_listeners:
                cb(suffix, payload)

        for cb in self._listeners.get(suffix, []):
            cb(payload)

    def subscribe_state(self, field: str, callback: Callable[[str], None]) -> None:
        self._listeners[field].append(callback)

    def subscribe_availability(self, callback: Callable[[bool], None]) -> None:
        self._availability_listeners.append(callback)

    def subscribe_soil(self, callback: Callable[[str, str], None]) -> None:
        self._soil_listeners.append(callback)

    def publish(self, topic: str, payload: str) -> None:
        _LOGGER.debug("Publishing %s → %s", topic, payload)
        self._client.publish(topic, payload)

    def stop(self) -> None:
        if not self._started:
            return
        self._client.loop_stop()
        self._client.disconnect()
