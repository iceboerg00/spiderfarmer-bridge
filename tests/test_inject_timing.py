"""Inject must wait for the upstream CONNACK before pushing PUBLISH packets
to the controller. Otherwise the controller — still in MQTT CONNECTING state —
treats the unsolicited DOWN PUBLISH as a protocol violation and drops the TLS
connection. Symptom: rapid reconnect loop when HA spams a command on every
availability=online event.
"""

import asyncio
import json
from unittest.mock import MagicMock

import proxy.mitm_proxy as mitm_proxy
from proxy.mitm_proxy import ProxySession
from proxy.mqtt_parser import parse_packets, MQTT_PUBLISH


def _make_writer():
    """Build a stand-in for asyncio.StreamWriter with awaitable drain()."""
    writer = MagicMock()
    writer.write = MagicMock()

    async def _drain():
        return None
    writer.drain = _drain
    return writer


PAYLOAD = {
    "method": "setConfigField",
    "params": {"keyPath": ["device", "blower"],
               "blower": {"mOnOff": 1, "mLevel": 39}},
    "pid": "AABBCC",
    "msgId": "0",
    "uid": "uid1",
}


def test_inject_blocks_until_ready_event_is_set(monkeypatch):
    """If _ready is never set, inject must time out and not write anything."""
    monkeypatch.setattr(mitm_proxy, "INJECT_READY_TIMEOUT", 0.05)

    async def run():
        session = ProxySession("ggs_1", "AABBCC", "uid1", MagicMock())
        writer = _make_writer()
        session.set_client(writer)
        # _ready is intentionally NOT set
        await session.inject(PAYLOAD)
        writer.write.assert_not_called()

    asyncio.run(run())


def test_inject_proceeds_when_ready_set_before_call(monkeypatch):
    monkeypatch.setattr(mitm_proxy, "INJECT_READY_TIMEOUT", 1.0)

    async def run():
        session = ProxySession("ggs_1", "AABBCC", "uid1", MagicMock())
        writer = _make_writer()
        session.set_client(writer)
        session._ready.set()

        await session.inject(PAYLOAD)

        writer.write.assert_called_once()
        written = writer.write.call_args.args[0]
        # Must be a valid MQTT PUBLISH targeting the DOWN topic
        packets, _ = parse_packets(written)
        assert len(packets) == 1
        assert packets[0].packet_type == MQTT_PUBLISH
        assert packets[0].topic == "SF/GGS/CB/API/DOWN/AABBCC"
        assert json.loads(packets[0].message) == PAYLOAD

    asyncio.run(run())


def test_inject_proceeds_when_ready_set_during_wait(monkeypatch):
    """Realistic case: inject() is awaiting; CONNACK arrives during the wait."""
    monkeypatch.setattr(mitm_proxy, "INJECT_READY_TIMEOUT", 1.0)

    async def run():
        session = ProxySession("ggs_1", "AABBCC", "uid1", MagicMock())
        writer = _make_writer()
        session.set_client(writer)

        async def fire_ready_after_50ms():
            await asyncio.sleep(0.05)
            session._ready.set()

        await asyncio.gather(
            session.inject(PAYLOAD),
            fire_ready_after_50ms(),
        )
        writer.write.assert_called_once()

    asyncio.run(run())


def test_inject_without_writer_returns_silently():
    """No client writer → nothing to do, no crash."""
    async def run():
        session = ProxySession("ggs_1", "AABBCC", "uid1", MagicMock())
        # set_client never called
        await session.inject(PAYLOAD)  # must not raise

    asyncio.run(run())
