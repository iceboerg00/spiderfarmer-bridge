# Extending the Bridge — Adding New Modules / Settings to HA

Practical playbook for the next time the SF App grows a new screen, or the
controller gains a new field we want exposed in Home Assistant. Pairs with
[`sf-protocol.md`](sf-protocol.md), which is the protocol reference; this
doc is the recipe.

The fan and light app-parity work (`feat/fan-app-parity`) is the canonical
worked example — read those diffs alongside this guide.

---

## Architecture in 30 seconds

Three layers, three files, one direction each:

```
device → cloud  ┐
                ├─►  proxy/normalizer.py  ─►  HA state topics
HA → device     │    proxy/command_handler.py  ─►  setConfigField
                └    ha/discovery.py  ─►  HA MQTT discovery
```

- **`proxy/normalizer.py`** — turns whatever shape the controller sends
  (`getDevSta` / `getConfigField` response / observed cloud
  `setConfigField`) into flat `state/...` topics for HA.
- **`proxy/command_handler.py`** — turns HA `command/.../set` payloads
  into `setConfigField` requests for the controller.
- **`ha/discovery.py`** — emits the static MQTT-discovery configs telling
  HA which entities exist and which topics they live on.

`proxy/mitm_proxy.py` glues these together. You usually don't need to
touch it — it already caches observed cloud state in
`session.fan_state` / `session.light_state` / `session.device_state`,
publishes per-field state on cache write, and routes incoming
`/command/<field>/<subfield>/set` topics to `translate_command`.

---

## Step 0 — Capture real traffic first

Never invent field names. Capture what the SF App actually sends and the
controller actually returns.

1. Set the controller to talk through the proxy (DNS hijack already in
   place if the bridge is running).
2. Tail the proxy log and filter for the module you care about:
   ```bash
   ssh pi@<host> 'pm2 logs spiderbridge-proxy --lines 0' | grep -i 'setConfigField\|<module>'
   ```
3. In the SF App, click through every option on the new screen — every
   toggle, slider, mode dropdown. Watch each click produce one
   `setConfigField` capture.
4. Save the JSON for later. The interesting bits are the **`params.<module>`
   block** (full field set) and `params.keyPath` (`["device", "<module>"]`
   or `["outlet", "O3"]`).

If `getConfigField` is supported for your module, also capture a
CONFIG-RESP — the bridge already polls those every 10 minutes and on
session connect, so they show up automatically once you enable polling
for the new keypath (`MITMProxy.poll_session_config` in `mitm_proxy.py`).

---

## Step 1 — Decide the entity shape in HA

Pick from the existing patterns:

| Controller field type     | HA entity   | Helper in `discovery.py`      |
|---------------------------|-------------|--------------------------------|
| 0/1 toggle                | `switch`    | `_switch_path`                 |
| Numeric (clamped range)   | `number`    | `_number_path`                 |
| `HH:MM` time              | `text`      | `_text_path` (with regex)      |
| Mode dropdown             | `select` or `fan.preset_modes` | inline   |
| RGB / brightness          | `light`     | `_light` (json schema)         |
| Read-only metric          | `sensor`    | `_sensor`                      |

If the new screen has multiple settings groups (the SF App's "Lampe
Einstellungen" splits into Schedule, PPFD, Temperaturschutz), use
**sub-devices** so HA renders them as separate cards. See
`_settings_subdevice()` and how `_fan_extras()` / `_light_extras()` use
it: each card gets its own `identifiers` and a `via_device` pointing at
the main controller.

If a single field belongs in multiple cards (Temperaturschutz applies in
both Schedule and PPFD modes), use `_number_path_aliased()` — same wire
topics, distinct unique_ids, both cards stay synchronized.

---

## Step 2 — Normalizer (controller → HA state topics)

In `proxy/normalizer.py`:

1. If the new module is a **block** under `data.<module>` (like fan,
   light), add a top-level entry in `normalize_status` and an
   `<module>_extras_topics()` helper modeled on `fan_extras_topics` /
   `light_extras_topics`. The helper publishes one MQTT topic per HA
   entity under `spiderfarmer/{device_id}/state/<module>/<suffix>`.

2. Use the **cache-merge pattern** when the controller reports partial
   updates: minimal `getDevSta` carries only `{on, level}` for some
   firmwares, so merge against the cached full block before publishing
   extras:
   ```python
   merged = {**cache.get(module, {}), **block_from_devsta}
   result.update(<module>_extras_topics(device_id, module, merged))
   ```

3. If the module needs a `mode_label` (preset_mode dropdown), keep the
   `_FAN_MODES` / `_LIGHT_MODES` dict in the normalizer as the single
   source of truth — the discovery and command_handler reverse-map from
   it.

4. Add tests in `tests/test_normalizer.py` covering: full block, partial
   update with cache fallback, the mode_label mapping for every known
   `modeType`.

---

## Step 3 — Discovery (HA entities)

In `ha/discovery.py`:

1. Add an `_<module>_extras()` function returning a list of
   `(topic, payload)` tuples. Use the existing helpers — don't roll
   your own.

2. Wire it in `publish_discovery_for_device`:
   ```python
   entities.append(_<module>(device_id, ...))      # main entity
   entities += _<module>_extras(device_id, ...)    # settings sub-devices
   ```

3. Sub-device naming convention:
   `spiderfarmer_{device_id}_<module>_<group>` (e.g.
   `spiderfarmer_ggs_1_light_schedule`). Matches the slug used in
   `_settings_subdevice()`.

4. Add tests in `tests/test_discovery.py`. The existing tests check:
   the topics are emitted, sub-device `identifiers` and `via_device`
   are correct, ranges and units match, retain flag is set. Mirror
   that pattern.

---

## Step 4 — Command handler (HA → controller)

In `proxy/command_handler.py`:

1. Define a `_<MODULE>_SUBFIELDS = {...}` set of every entity suffix
   the new HA card writes back to.

2. Branch on `if field == "<module>" and subfield in _<MODULE>_SUBFIELDS`
   **before** any catch-all branch for the same field.

3. **Cache + synthesize fallback.** Always start from a copy of the
   cached block so untouched fields survive the round-trip. When the
   cache is empty, synthesize a sensible default block — partial
   `setConfigField` payloads get silently rejected by some firmwares.
   See the fan/light branches for templates.

4. For numeric subfields: clamp to the range HA published in discovery.
   For `HH:MM` text: use `_hhmm_to_seconds`. For mode dropdowns: reverse
   lookup against the same dict the normalizer uses.

5. Pass any new cache parameter through:
   - Add `<module>_state: Optional[dict] = None` to `translate_command`.
   - In `mitm_proxy.handle_command`, pass `<module>_state=session.<module>_state`.
   - Add the cache field to `ProxySession.__init__`.
   - In `relay_down` (cloud → device observation), populate the cache
     when you see a setConfigField for the module, and publish the
     normalizer's per-field state topics so HA stays in sync.
   - In `handle_command` (HA → device), do the same optimistic update
     after `session.inject(payload)` — HA shouldn't have to wait for
     the next poll to see its own change.

6. Tests in `tests/test_command_handler.py`: one per subfield (happy
   path), clamping at min/max, invalid input → `None`, empty cache
   synthesizes defaults, cached block fields untouched outside the
   target subfield.

---

## Step 5 — Wire periodic config polling (if the module supports it)

`MITMProxy.poll_session_config` in `mitm_proxy.py` already injects
`getConfigField` for `light`, `light2`, `fan`, `blower` every 10 minutes
and on session connect. If your new module returns useful data via
`getConfigField`, add its keypath to that list:

```python
for keypath in (["device", "light"], ["device", "light2"],
                ["device", "fan"], ["device", "blower"],
                ["device", "<your_module>"]):
```

If the controller does **not** support `getConfigField` for that module
(some don't — silent timeout), fall back to caching from observed cloud
`setConfigField` traffic only. The fan/light pattern handles both.

---

## Step 6 — Sync to the addon path

Anything you change under `proxy/` or `ha/` must be mirrored under
`spiderbridge/app/proxy/` and `spiderbridge/app/ha/` for the HA OS addon.
The two `mitm_proxy.py` files differ only in `_save_config()` (the addon
writes `/data/devices.yaml` when running under HA OS). All other files
are byte-identical — copy them straight over.

```bash
cp proxy/<file>.py spiderbridge/app/proxy/<file>.py
cp ha/discovery.py spiderbridge/app/ha/discovery.py
cp tests/test_<file>.py spiderbridge/app/tests/test_<file>.py
```

Run both test suites:

```bash
python -m pytest tests/                   # standalone
cd spiderbridge/app && python -m pytest tests/   # addon
```

The addon adds `tests/test_config_ha.py` on top — that's expected.

---

## Step 7 — Verify on a real device

The unit tests catch shape errors, not behavior. Final check:

1. Push the branch to the Pi: `git push && ssh pi@<host> 'cd /opt/spiderbridge && git pull && pm2 restart all'`
   (or follow whatever deploy flow `update.sh` does).
2. Open HA → device page → confirm new entities appear and load values.
3. Click each new entity. In the proxy log you should see one `setConfigField`
   per click, with the field you just changed. Compare it to the SF App
   capture from Step 0 — they should be byte-equivalent (modulo
   `msgId` / `uid`).
4. Wait 10 minutes (or restart the proxy). The first config poll should
   bring the controller's current values back and HA should reflect them.
5. Change the same setting from the SF App. The proxy logs should
   observe it; HA should update within seconds via `relay_down`'s
   cache + extras-topic publish.

If a click in HA produces no observable change on the controller, 90% of
the time the cause is one of:

- Wrong DOWN topic prefix (PS5/PS10 use a different prefix than CB —
  `session.down_topic_prefix` is learned from observed cloud commands).
  Symptom: the inject leaves the proxy but the controller never executes
  it. Fix: trigger one click from the SF App first so the prefix gets
  learned.
- Cache empty + synthesized defaults missing a required field. Symptom:
  controller silently rejects (no echo, no state change). Fix: capture
  the App's full payload from Step 0 and add the missing field to the
  synthesized default block in `command_handler.py`.
- The module's keypath isn't in `poll_session_config` and no observed
  `setConfigField` has populated the cache yet. Symptom: first HA write
  works (synthesized default), subsequent writes wipe other fields. Fix:
  add the keypath to the poll list.

---

## Reference: the fan and light app-parity diffs

These two features are the worked examples to copy from. They cover all
three layers, both standalone + addon paths, both modes of cache
population (poll + cloud observation), and both single-device and
sub-device entity grouping.

Look at the git log for `feat/fan-app-parity`. The commits there are
deliberately grouped so each layer is one commit:

1. normalizer changes + tests
2. discovery changes + tests
3. command_handler changes + tests
4. mitm_proxy wiring (caches + polling + optimistic updates)
5. addon path sync

Use that as a checklist for your own module.
