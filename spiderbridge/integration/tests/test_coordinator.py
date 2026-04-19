import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import MagicMock, patch
from spiderbridge.coordinator import MQTTCoordinator


def _make_coordinator(device_id="ggs_1"):
    hass = MagicMock()
    hass.loop = MagicMock()
    hass.loop.call_soon_threadsafe.side_effect = lambda fn, *args: fn(*args)
    with patch("spiderbridge.coordinator.mqtt.Client") as mock_client_cls:
        mock_client_cls.return_value = MagicMock()
        coord = MQTTCoordinator(hass, device_id)
    return coord


def test_dispatch_state_calls_listener():
    coordinator = _make_coordinator()
    received = []
    coordinator.subscribe_state("temperature", lambda p: received.append(p))
    coordinator._dispatch("spiderfarmer/ggs_1/state/temperature", "22.5")
    assert received == ["22.5"]


def test_dispatch_availability_online():
    coordinator = _make_coordinator()
    states = []
    coordinator.subscribe_availability(lambda avail: states.append(avail))
    coordinator._dispatch("spiderfarmer/ggs_1/availability", "online")
    assert states == [True]


def test_dispatch_availability_offline():
    coordinator = _make_coordinator()
    states = []
    coordinator.subscribe_availability(lambda avail: states.append(avail))
    coordinator._dispatch("spiderfarmer/ggs_1/availability", "offline")
    assert states == [False]


def test_dispatch_soil_calls_soil_listener():
    coordinator = _make_coordinator()
    received = []
    coordinator.subscribe_soil(lambda suffix, payload: received.append((suffix, payload)))
    coordinator._dispatch("spiderfarmer/ggs_1/state/soil_ABC123_temp", "25.0")
    assert received == [("soil_ABC123_temp", "25.0")]


def test_dispatch_soil_also_calls_state_listener():
    coordinator = _make_coordinator()
    received = []
    coordinator.subscribe_state("soil_ABC123_temp", lambda p: received.append(p))
    coordinator._dispatch("spiderfarmer/ggs_1/state/soil_ABC123_temp", "25.0")
    assert received == ["25.0"]


def test_dispatch_unknown_topic_ignored():
    coordinator = _make_coordinator()
    received = []
    coordinator.subscribe_state("temperature", lambda p: received.append(p))
    coordinator._dispatch("spiderfarmer/ggs_1/state/humidity", "60.0")
    assert received == []


def test_multiple_listeners_on_same_field():
    coordinator = _make_coordinator()
    a, b = [], []
    coordinator.subscribe_state("temperature", lambda p: a.append(p))
    coordinator.subscribe_state("temperature", lambda p: b.append(p))
    coordinator._dispatch("spiderfarmer/ggs_1/state/temperature", "23.0")
    assert a == ["23.0"] and b == ["23.0"]


def test_on_message_dispatches_to_listener():
    coordinator = _make_coordinator()
    received = []
    coordinator.subscribe_state("temperature", lambda p: received.append(p))
    msg = MagicMock()
    msg.topic = "spiderfarmer/ggs_1/state/temperature"
    msg.payload = b"19.0"
    coordinator._on_message(None, None, msg)
    assert received == ["19.0"]
