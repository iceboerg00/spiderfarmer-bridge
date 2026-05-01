<p align="center">
  <img src="logo.png" alt="SpiderBridge Logo" width="400"/>
</p>

Local bridge for the Spider Farmer GGS Controller → Home Assistant via MQTT Discovery.

A Raspberry Pi acts as a Wi-Fi hotspot for the GGS Controller. The Pi intercepts the MQTT/TLS traffic, normalizes the data, and makes it available to Home Assistant. The official Spider Farmer app and cloud continue to work in parallel.

```
GGS Controller
     │  Wi-Fi (hotspot on Pi)
     ▼
Raspberry Pi ──── TLS MITM Proxy :8883
     │                      │
     │  eth0 (LAN)      Mosquitto :1883
     │                      │
     ▼                      ▼
  SF Cloud            Home Assistant
  (app keeps          (entities auto-
   working)            discovered)
```

---

## Supported Modules

SpiderBridge has been confirmed working with the following modules. Multiple modules can run on the same controller simultaneously — entities for each are auto-discovered.

| Module | Sensors / Lights | Outlets | HA control |
|---|---|---|---|
| Control Box (CB) | Air, soil, CO₂, PPFD, lights, fans, climate accessories | — | full |
| Power Strip 5 (PS5) | Air sensors, lights, blower/fan | 5 | on/off* |
| Power Strip 10 (PS10) | Air sensors, lights, blower/fan | 10 | on/off* |
| Light Controller (LC) | 2 light channels with brightness, mode, PPFD | — | partial |

\* PS5/PS10 outlet control requires the SF App to have toggled each outlet at least once after a proxy restart, so the proxy can learn the per-outlet schedule the controller expects (see *PS5/PS10 Outlet "Training"* below).

---

## Two Installation Options

### Option A — HA Add-on (recommended)

Everything runs directly on your Home Assistant device. No separate Pi needed.

**Requirements:**
- Raspberry Pi running HAOS with Wi-Fi (wlan0)
- **LAN cable (eth0) mandatory** — the Pi must be connected to your main network via Ethernet. Wi-Fi (wlan0) is fully occupied by the hotspot for the GGS Controller and cannot be used for the home network at the same time.

**Setup:**

1. In Home Assistant: **Settings → Add-ons → Add-on Store → ⋮ → Repositories**

   Add: `https://github.com/iceboerg00/spiderfarmer-bridge`

2. Install **SpiderBridge** from the store

3. Configure options:

   | Option | Description |
   |--------|-------------|
   | `ssid` | Wi-Fi network name the GGS Controller connects to |
   | `password` | Wi-Fi password (min. 8 characters) |
   | `channel` | 2.4 GHz channel (1–11) |
   | `hotspot_ip` | Gateway IP for the hotspot (default: `192.168.10.1`) |
   | `device_name` | Friendly name in Home Assistant |
   | `hotspot_enabled` | Enable/disable the Wi-Fi hotspot |

4. Start the add-on

5. **Restart Home Assistant Core** (Settings → System → Restart)

6. Go to **Settings → Devices & Services → Add Integration → SpiderBridge**

   One click — no further configuration needed.

7. Connect the GGS Controller to the configured Wi-Fi SSID

On first connect, the GGS Controller MAC is auto-detected. All entities appear automatically under one device.

> **Note:** The latest PS5/PS10 outlet-control fixes are deployed in Option B first. The HA add-on currently supports CB outlets fully; PS5/PS10 outlet *control* may not yet work in the add-on path. Sensors, lights, and fans are unaffected.

---

### Option B — Standalone Pi + MQTT

SpiderBridge runs on a dedicated Raspberry Pi (any model with Wi-Fi). Home Assistant connects to the Pi's Mosquitto broker on port 1883 to receive data.

**Requirements:**
- Raspberry Pi with Raspberry Pi OS (64-bit) and Wi-Fi
- **LAN cable (eth0) mandatory** — same reason as Option A: wlan0 is used as a hotspot for the GGS Controller, so Ethernet is the only way to reach the internet and your Home Assistant instance
- Home Assistant on another device in the same network with an MQTT broker (or use the Pi's local Mosquitto)

**Installation:**

```bash
curl -sSL https://raw.githubusercontent.com/iceboerg00/spiderfarmer-bridge/master/setup/bootstrap.sh | sudo bash
```

The installer will:
1. Clone this repository to `/opt/spiderfarmer-bridge`
2. Run an interactive setup wizard (SSID, password, device name)
3. Configure Mosquitto, Python venv, TLS certificates, and **pm2-managed services** (`sf-proxy`, `sf-discovery`)
4. Set up the Wi-Fi hotspot with stability tweaks (powersave off, PMF disabled — required for the GGS Controller to stay associated)

**Home Assistant setup:**

Go to **Settings → Devices & Services → MQTT → Configure**:

| Field | Value |
|-------|-------|
| Broker | IP address of the Pi (eth0, e.g. `192.168.1.100`) |
| Port | `1883` |
| Username | leave empty |
| Password | leave empty |

All entities appear automatically via MQTT Discovery under one device.

---

## Available Entities

Once the GGS Controller connects, the following entities are published. Which ones appear depends on the connected modules.

| Type | Entities |
|------|----------|
| Sensor | Air Temperature, Humidity, VPD, CO₂, PPFD |
| Sensor | Soil Temperature / Humidity / EC (average + per sensor) |
| Light | Light 1 + Light 2 (on/off, brightness, mode: Manual/Timer, PPFD) |
| Fan | Fan Exhaust (on/off + speed 0–100%) |
| Fan | Fan Circulation (on/off + speed 0–10) |
| Switch | Heater, Humidifier, Dehumidifier |
| Switch | Outlet 1–10 (count depends on the connected Power Strip) |

Soil sensors are auto-discovered with their hardware ID on first connect.

---

## PS5/PS10 Outlet "Training"

Power Strip controllers reject minimal `{modeType, mOnOff}` commands — they require the full per-outlet block (cycle schedule, time periods, temp/humi compensation, optional watering binding). The proxy learns this block by observing what the SF Cloud sends; HA toggles then replay the same shape with only the on/off state changed.

In practice this means:

- **First-time setup:** open the SF App and toggle each PS5/PS10 outlet you want to control from HA at least once. The proxy stores the full block per outlet in memory.
- **After every `sudo pm2 restart sf-proxy` or Pi reboot:** repeat the App-toggle once per outlet (the cache lives in RAM).
- After "training" an outlet, HA on/off control works permanently for that outlet — until the cache is cleared.

If you toggle an outlet from HA before it has been trained, the proxy falls back to a minimal command. CB outlets accept it; PS5/PS10 outlets ignore it. The next App-toggle then primes the cache.

---

## First Connection (both options)

After starting, connect the GGS Controller to the configured Wi-Fi SSID. The MAC address is auto-detected on first connect:

```
┌─────────────────────────────────────────────┐
│  🕷  SpiderBridge — Gerät erkannt           │
│  MAC: 7C2C67F03DAC                          │
│  ID:  Spider Farmer GGS                     │
└─────────────────────────────────────────────┘
```

---

## Hotspot Toggle (Option A only)

Set `hotspot_enabled: false` in the add-on options if the GGS Controller connects via your existing router instead. The proxy continues to intercept traffic on port 8883 — only the built-in hotspot is disabled.

---

## Managing Services (Option B only)

Services are managed by **pm2**, not systemd. The systemd unit files in the repo are unused.

```bash
sudo pm2 status                       # Show service state
sudo pm2 logs sf-proxy                # Live proxy log
sudo pm2 logs sf-proxy --lines 200    # Last 200 lines
sudo pm2 restart sf-proxy             # Restart proxy
sudo pm2 restart sf-discovery         # Restart discovery service
```

Watch all MQTT topics that the bridge publishes:

```bash
mosquitto_sub -h localhost -p 1883 -t 'spiderfarmer/#' -v
```

Updating to the latest version:

```bash
sudo git -C /opt/spiderfarmer-bridge pull
sudo pm2 restart sf-proxy
```

---

## Troubleshooting

**Controller does not connect to hotspot**
- GGS Controller supports 2.4 GHz only — use channels 1–11
- Option A: check add-on log for `AP-ENABLED`
- Option B: `nmcli con show SF-Bridge-Hotspot | grep band` and verify `802-11-wireless.powersave` is `2` (disabled). Older installs without the stability tweaks dropped daily.

**No data in Home Assistant**
- Option A: check add-on log for `Proxy listening on 0.0.0.0:8883`
- Option B: `sudo pm2 logs sf-proxy --lines 100`
- Verify MQTT topics: `mosquitto_sub -h <pi-ip> -p 1883 -t 'spiderfarmer/#' -v`

**HA outlet toggle has no effect on a PS5/PS10**
- See *PS5/PS10 Outlet "Training"* above. Toggle the outlet from the SF App once after every proxy restart, then HA control works.
- Check `sudo pm2 logs sf-proxy | grep "Using cached"` — if you see this line during HA toggles, the proxy is correctly replaying a cached block.
- Check `sudo pm2 logs sf-proxy | grep "DOWN topic prefix"` — the proxy auto-detects whether the controller uses `CB`, `PS`, `LC` etc. as topic prefix; if it never sees the cloud commanding the device, the prefix stays at the default `CB` and may not match.

**Entities show as unavailable**
- Accessories (heater, humidifier, etc.) only appear after the controller reports their state
- Option A: restart the add-on
- Option B: `sudo pm2 restart sf-discovery`

**Integration not showing after add-on update (Option A)**
- Restart Home Assistant Core after each add-on update that changes the integration
- The add-on installs the integration on every start — a Core restart is required to pick up changes

---

## Project Structure

```
spiderfarmer-bridge/
├── proxy/           # MQTT parser, normalizer, command handler, MITM proxy
├── ha/              # HA Discovery payloads and publisher
├── config/          # config.yaml, mosquitto.conf
├── setup/           # bootstrap.sh, install.sh, wizard.sh, hotspot.sh
├── certs/           # TLS certificates
├── tests/           # Unit tests (pytest)
├── spiderbridge/    # HA Add-on (Option A)
│   ├── config.yaml
│   ├── Dockerfile
│   ├── app/         # Python code for the container
│   ├── integration/ # HA custom integration (auto-installed by add-on)
│   └── rootfs/      # s6 service scripts
└── repository.yaml  # HA custom repository definition
```

---

## Tests (Option B)

```bash
cd /opt/spiderfarmer-bridge
.venv/bin/pytest tests/ -v
```
