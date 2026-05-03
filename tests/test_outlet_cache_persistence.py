"""Persistence of the per-outlet block cache across ProxySession instances.

PS5/PS10 controllers ignore minimal toggle commands; the proxy learns the
full per-outlet block by observing cloud→device traffic. Without disk
persistence, every Pi reboot or pm2 restart drops the cache and the user
has to re-train each outlet via the SF App. The tests below verify the
on-disk format and round-trip correctness.
"""
from pathlib import Path
from unittest.mock import MagicMock

from proxy.mitm_proxy import ProxySession


def _make_session(device_id: str, cache_dir: Path) -> ProxySession:
    return ProxySession(
        device_id=device_id,
        mac="AABBCCDDEEFF",
        uid="uid1",
        mqtt_client=MagicMock(),
        cache_dir=cache_dir,
    )


def test_outlet_cache_round_trip(tmp_path: Path):
    s1 = _make_session("ggs_1", tmp_path)
    assert s1.outlet_state == {}

    s1.outlet_state["O1"] = {"modeType": 0, "mOnOff": 1, "tempAdd": 2}
    s1.outlet_state["O3"] = {"modeType": 0, "mOnOff": 0, "wateringEnv": {"extra": {"enabled": 0}}}
    s1._save_outlet_cache()

    # Fresh session with same cache_dir must see the same blocks
    s2 = _make_session("ggs_1", tmp_path)
    assert s2.outlet_state == s1.outlet_state


def test_outlet_cache_isolated_per_device(tmp_path: Path):
    # Two devices sharing one cache file must not bleed into each other
    a = _make_session("ggs_a", tmp_path)
    b = _make_session("ggs_b", tmp_path)
    a.outlet_state["O1"] = {"mOnOff": 1}
    b.outlet_state["O2"] = {"mOnOff": 0}
    a._save_outlet_cache()
    b._save_outlet_cache()

    a_reload = _make_session("ggs_a", tmp_path)
    b_reload = _make_session("ggs_b", tmp_path)
    assert a_reload.outlet_state == {"O1": {"mOnOff": 1}}
    assert b_reload.outlet_state == {"O2": {"mOnOff": 0}}


def test_outlet_cache_disabled_when_no_cache_dir():
    # Without a cache_dir the session never touches disk: load returns empty
    # and save is a no-op (no path errors).
    s = ProxySession("ggs_1", "AABBCCDDEEFF", "uid1", MagicMock(), cache_dir=None)
    assert s.outlet_state == {}
    s.outlet_state["O1"] = {"mOnOff": 1}
    s._save_outlet_cache()  # must not raise


def test_outlet_cache_corrupt_file_falls_back_to_empty(tmp_path: Path):
    # If the cache file is malformed we must not crash — start with an
    # empty cache and let the next observation overwrite the bad file.
    cache_file = tmp_path / "outlet_cache.json"
    cache_file.write_text("not json at all")
    s = _make_session("ggs_1", tmp_path)
    assert s.outlet_state == {}


def test_outlet_cache_save_uses_atomic_replace(tmp_path: Path):
    # The save path writes to a .tmp sibling and renames; verify no .tmp
    # leftover after save and that the final file is valid JSON.
    s = _make_session("ggs_1", tmp_path)
    s.outlet_state["O1"] = {"mOnOff": 1}
    s._save_outlet_cache()

    cache_file = tmp_path / "outlet_cache.json"
    tmp_file = tmp_path / "outlet_cache.json.tmp"
    assert cache_file.exists()
    assert not tmp_file.exists()
    import json
    payload = json.loads(cache_file.read_text())
    assert payload == {"ggs_1": {"O1": {"mOnOff": 1}}}
