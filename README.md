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

---

### Option B — Standalone Pi + MQTT

SpiderBridge runs on a dedicated Raspberry Pi (any model with Wi-Fi). Home Assistant connects to the Pi's Mosquitto broker on port 1883 to receive data.

**Requirements:**
- Raspberry Pi with Raspberry Pi OS (64-bit) and Wi-Fi
- **LAN cable (eth0) mandatory** — same reason as Option A: wlan0 is used as a hotspot for the GGS Controller, so Ethernet is the only way to reach the internet and your Home Assistant instance
- Home Assistant on another device in the same network

**Installation:**

```bash
curl -sSL https://raw.githubusercontent.com/iceboerg00/spiderfarmer-bridge/master/setup/bootstrap.sh | sudo bash
```

The installer will:
1. Clone this repository to `/opt/spiderfarmer-bridge`
2. Run an interactive setup wizard (SSID, password, device name)
3. Configure Mosquitto, Python venv, TLS certificates, and systemd services
4. Set up the Wi-Fi hotspot

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

Once the GGS Controller connects, the following entities appear in Home Assistant:

| Type | Entities |
|------|----------|
| Sensor | Air Temperature, Humidity, VPD |
| Sensor | Soil Temperature / Humidity / EC (average + per sensor) |
| Light | Light 1 + Light 2 (on/off, brightness, mode: Manual/Timer, PPFD) |
| Fan | Fan Exhaust (on/off + speed 0–100%) |
| Fan | Fan Circulation (on/off + speed 0–10) |
| Switch | Heater, Humidifier, Dehumidifier |
| Switch | Outlet 1–10 |

Soil sensors are auto-discovered with their hardware ID on first connect.

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

```bash
sudo systemctl status sf-proxy      # Proxy status
sudo systemctl status sf-discovery  # Discovery status
sudo journalctl -u sf-proxy -f      # Live proxy log
```

```bash
mosquitto_sub -h localhost -p 1883 -t 'spiderfarmer/#' -v  # Watch all MQTT topics
```

---

## Troubleshooting

**Controller does not connect to hotspot**
- GGS Controller supports 2.4 GHz only — use channels 1–11
- Option A: check add-on log for `AP-ENABLED`
- Option B: `nmcli con show SF-Bridge-Hotspot | grep band`

**No data in Home Assistant**
- Option A: check add-on log for `Proxy listening on 0.0.0.0:8883`
- Option B: watch proxy log with `sudo journalctl -u sf-proxy -f`
- Verify MQTT topics: `mosquitto_sub -h <pi-ip> -p 1883 -t 'spiderfarmer/#' -v`

**Entities show as unavailable**
- Accessories (heater, humidifier, etc.) only appear after the controller reports their state
- Option A: restart the add-on
- Option B: `sudo systemctl restart sf-discovery`

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
