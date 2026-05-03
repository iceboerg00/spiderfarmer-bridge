# Spider Farmer GGS Protocol — Reverse-Engineered Notes

What we have learned about the SF cloud ↔ controller protocol while building
this bridge. Distilled from packet captures, the bundled `schedule-4-real`
proxy (PyInstaller-decompiled), and lots of trial and error.

This is **not** an official spec. Fields and modeType numbers may vary
between firmware versions. Treat as a working reference, not a guarantee.

---

## Transport

- The controller talks MQTT-over-TLS to `sf.mqtt.spider-farmer.com:8883`.
- The Pi proxy intercepts via DNS redirect + iptables NAT to port 8883 on
  the hotspot interface, terminates TLS, re-establishes upstream TLS to the
  real cloud, and forwards both directions.
- The cloud presents a private CA — we ship the SF certs in `certs/` (CA,
  client cert, client key). mTLS is required upstream; client-side TLS uses
  our own cert that the controller already trusts (firmware-pinned).

## Topic structure

```
SF/GGS/{prefix}/API/{UP|DOWN}/{MAC}
```

- `prefix`: per-controller, learned at runtime. Confirmed values:
  - `CB` — Control Box
  - `PS` — Power Strip 5/10
  - `LC` — Light Controller
  - More variants likely exist.
- `UP` — controller → cloud (status, ack, getDevSta responses).
- `DOWN` — cloud → controller (commands, getDevSta polls).
- `{MAC}` — device MAC, uppercase, no separators (e.g. `7C2C67F03DAC`).

The proxy learns the prefix the moment the controller subscribes after
`CONNECT`, so HA outlet/light/fan toggles target the right topic from the
very first command.

## Methods seen on DOWN (cloud → device)

| Method | Purpose |
|---|---|
| `getDevSta` | Cloud asks "what's your current state?". Response on UP carries minimal fields (mOnOff, mLevel, modeType for each module). |
| `getDevOpLog` | Cloud polls operation log entries, paginated by `id`. |
| `getSysSta` | System status — firmware version, etc. |
| `setConfigField` | Write configuration. Carries the full per-module block. |
| `getConfigField` | Read config — but in our experience the controller does **not** answer proxy-injected `getConfigField`. May be auth-gated to the SF App. |

## `setConfigField` payload shape

```json
{
  "method": "setConfigField",
  "pid": "7C2C67F03DAC",
  "params": {
    "keyPath": ["device", "light"],
    "light": { … full module block … }
  },
  "msgId": "1770622729475",
  "uid": "36656"
}
```

- `keyPath` is `[domain, module]`, e.g. `["device", "light"]`,
  `["device", "fan"]`, `["outlet", "O3"]`.
- The block under the module key carries every field the controller knows
  about that module — schedule, mode, current state. Partial updates work
  for some modules (outlets accept `{modeType, mOnOff}` once the topic
  prefix is right) but not others (lights need a complete-enough block).

## `msgId` format

Stringified millisecond Unix timestamp (13 digits). Our proxy synthesizes
the same width when it injects so the controller doesn't reject us based
on length.

---

## Module: `light` / `light2`

### `modeType`

| Value | App label |
|---|---|
| 0 | Manueller Modus |
| 1 | Zeitfenstermodus |
| 12 | PPFD |

Higher numbers presumably exist for cycle/sunrise modes — not yet
confirmed.

### Field map (full setConfigField example)

```json
"light": {
  "modeType": 1,
  "lastAutoModeType": 1,
  "darkTemp": 0.0,
  "offTemp": 0.0,
  "timePeriod": [{
    "enabled": 1, "weekmask": 127,
    "startTime": 21600, "endTime": 0,
    "brightness": 66, "fadeTime": 900
  }],
  "ppfdPeriod": [{
    "enabled": 1, "weekmask": 127,
    "startTime": 360, "endTime": 0,
    "brightness": 20, "fadeTime": 180
  }],
  "ppfdMinBrightness": 13,
  "ppfdMaxBrightness": 97,
  "mOnOff": 1,
  "mLevel": 65
}
```

| Field | Meaning |
|---|---|
| `mOnOff` | 0/1 — current on/off state |
| `mLevel` | 0-100 — current brightness |
| `modeType` | see table above |
| `lastAutoModeType` | mirror of modeType (purpose unclear; copy along) |
| `darkTemp` | °C threshold for dimming. **0.0 = disabled** |
| `offTemp` | °C threshold for hard-off. **0.0 = disabled** |
| `timePeriod[]` | Schedule periods for Zeitfenstermodus |
| `timePeriod[i].startTime` / `endTime` | seconds since midnight, % 86400 |
| `timePeriod[i].weekmask` | bitfield, bit 0=Mon … bit 6=Sun. 127 = all days |
| `timePeriod[i].brightness` | target brightness during this period |
| `timePeriod[i].fadeTime` | sunrise/sunset fade in seconds |
| `timePeriod[i].enabled` | 0/1 |
| `ppfdPeriod[]` | Same shape as timePeriod, used in PPFD mode |
| `ppfdMinBrightness` | floor for PPFD-mode brightness |
| `ppfdMaxBrightness` | ceiling for PPFD-mode brightness |

### Light Controller (LC) flat schema

The standalone Light Controller reports state as **flat** keys at the top
level of `data` (i.e. `data.brightness`, `data.mode`) instead of nested
under `data.light`. Our normalizer handles both.

---

## Module: `fan` / `blower`

### `modeType`

Confirmed by clicking through every dropdown option in the SF App:

| Value | App label |
|---|---|
| 0 | Manueller Modus |
| 1 | Zeitfenstermodus |
| 2 | Zyklusmodus |
| 3 | Umweltmodus — Nur Temperatur |
| 4 | Umweltmodus — Nur Luftfeuchtigkeit |
| 7 | Umweltmodus — Temperatur priorisieren |
| 8 | Umweltmodus — Feuchtigkeit priorisieren |
| 13 | Umweltmodus — Temperatur & Luftfeuchtigkeit |

The "Betriebsmodus" sub-dropdown inside Umweltmodus is **not** a separate
field — it just maps to one of those modeType numbers. So the fan has
8 distinct modes total in `modeType`.

### Field map

```json
"fan": {
  "modeType": 2,
  "minSpeed": 1, "maxSpeed": 5,
  "shakeLevel": 6, "natural": 1,
  "mOnOff": 1, "mLevel": 3,
  "timePeriod": [{"enabled": 1, "weekmask": 127, "startTime": 3600, "endTime": 7200}],
  "cycleTime": {
    "weekmask": 127,
    "startTime": 10800,
    "openDur": 14400,
    "closeDur": 21600,
    "times": 2
  }
}
```

| Field | Meaning |
|---|---|
| `mOnOff` | Schalter (on/off) |
| `mLevel` | Gang in Manueller Modus (1-10), reflects current active speed |
| `maxSpeed` | Gang during scheduled active periods (Zeitfenster / Zyklus). 1-10 |
| `minSpeed` | Standby-Geschwindigkeit during inactive periods. **0 = Aus** |
| `shakeLevel` | Oszillation level, 0-10 |
| `natural` | Natürlicher Wind, 0/1 |
| `timePeriod[0]` | Zeitfenstermodus schedule (start/end in seconds) |
| `cycleTime.startTime` | Zyklusmodus: time of day when the cycle starts |
| `cycleTime.openDur` | Zyklusmodus: run time per cycle, seconds |
| `cycleTime.closeDur` | Zyklusmodus: off time per cycle, seconds |
| `cycleTime.times` | Number of executions per day. **Hard-capped at 100** by the controller, regardless of `openDur+closeDur` |

---

## Module: `outlet`

### Block shape

```json
"outlet": {
  "psmode": 1,
  "O1": { "on": 0 },
  "O2": { "on": 0 },
  …
  "O10": { "on": 0 }
}
```

`getDevSta` only reports the minimal `{on}` per outlet. `setConfigField`
carries the full per-outlet block including `cycleTime`, `timePeriod[]`,
`tempAdd`, `humiAdd`, optional `wateringEnv` and `bind` (sensor binding).

### keyPath for outlet writes

```
["outlet", "O3"]
```

### Outlet on/off command

Once the proxy has the right DOWN topic prefix, **a minimal payload is
enough** to switch an outlet on PS5/PS10:

```json
{ "modeType": 0, "mOnOff": 1 }
```

The controller preserves the rest (schedule, watering, sensor binding) on
its own. This was the breakthrough that made HA outlet control work
without needing to cache the full block.

### Field map

| Field | Meaning |
|---|---|
| `mOnOff` | on/off |
| `modeType` | 0 = Manuell. Other values follow a schedule/watering automation; we always force 0 on HA toggle |
| `psmode` | parent-level mode for the whole power strip. Not currently used |
| `cycleTime.times` | executions per day, used in scheduled outlet automation |
| `tempAdd` / `humiAdd` | per-outlet temperature / humidity offset for sensor logic |
| `wateringEnv` | watering automation block for sensor-bound outlets |
| `bind` | links the outlet to a soil sensor for `wateringEnv` to act on |

---

## Module: `sensors[]` / `sensor`

`data.sensor` carries **average** soil values (when only avg is reported)
plus the air-side sensors (`temp`, `humi`, `vpd`, `co2`, `ppfd`).

`data.sensors[]` is a list of per-sensor objects, each with:

```json
{ "id": "3839383705306F29", "tempSoil": 22.5, "humiSoil": 60.0, "ECSoil": 1.2 }
```

The special id `"avg"` is the average across all soil sensors and is
already covered by the top-level `data.sensor` block — we skip it during
per-sensor publishing to avoid duplicates.

---

## Behaviors observed

### DOWN topic prefix

Each controller subscribes to a specific DOWN prefix (`CB`, `PS`, `LC`).
Sending to the wrong prefix means the controller silently drops the
command. We learn the prefix from the controller's first SUBSCRIBE.

### Bluetooth bypass

When the SF App is connected to the controller via Bluetooth, settings
changes go directly over BLE and **bypass the cloud**. To capture
cloud-side packets you have to disable Bluetooth on the phone first;
otherwise our proxy never sees the change.

### Partial updates per module

| Module | Accepts partial setConfigField? |
|---|---|
| `outlet` | yes (just `{modeType, mOnOff}` is enough) |
| `light` / `light2` | partial mostly works for direct on/off, but mode changes need `timePeriod` populated |
| `fan` / `blower` | ditto — mode changes need the relevant block (`timePeriod` for Zeitfenster, `cycleTime` for Zyklus) |
| `heater` / `humidifier` / `dehumidifier` | minimal `{mOnOff}` works |

### `getConfigField` from proxy

Our proxy-injected `getConfigField` requests **time out** consistently —
the controller does not respond. The schedule-4-real proxy hits the same
behavior (its JS catches the timeout silently and falls back to a minimal
payload).

This is why our HA writes use a **cache** populated from observed cloud
setConfigField traffic, rather than fetching live state via
getConfigField. The cache lives in RAM only and gets seeded the first
time the SF App (with BT off) or the cloud sends a setConfigField for
that module.

---

## References

- `proxy/normalizer.py` — translates getDevSta into HA state topics
- `proxy/command_handler.py` — translates HA commands into setConfigField
- `proxy/mitm_proxy.py` — TLS termination, prefix learning, cache fill
- `ha/discovery.py` — HA MQTT Discovery configs (entities, sub-devices)
- `tools/decomp-output/` — local-only reverse-engineered notes from the
  schedule-4-real binary (gitignored)
