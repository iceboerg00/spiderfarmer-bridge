<p align="center">
  <img src="logo.png" alt="SpiderBridge Logo" width="400"/>
</p>

Local bridge for the Spider Farmer GGS Controller → Home Assistant via MQTT Discovery.

A Raspberry Pi 4 acts as a Wi-Fi hotspot for the GGS Controller. The Pi intercepts the MQTT/TLS traffic, normalizes the data, and publishes it to a local Mosquitto broker for Home Assistant. The official Spider Farmer app and cloud continue to work in parallel.

```
GGS Controller
     │  Wi-Fi (hotspot on Pi)
     ▼
Raspberry Pi 4 ──── TLS MITM Proxy :8883
     │                      │
     │  eth0 (LAN)      Mosquitto :1883
     │                      │
     ▼                      ▼
  SF Cloud            Home Assistant
  (app keeps          (MQTT Discovery,
   working)            auto entities)
```

---

## Installation

```bash
curl -sSL https://raw.githubusercontent.com/iceboerg00/spiderfarmer-bridge/master/setup/bootstrap.sh | sudo bash
```

The installer will:

1. Clone this repository to `/opt/spiderfarmer-bridge`
2. Run an interactive setup wizard (SSID, password, device name, HA MQTT credentials)
3. Configure Mosquitto, Python venv, TLS certificates, and PM2 services
4. Set up the Wi-Fi hotspot

**Requirements:**
- Raspberry Pi 4 with Raspberry Pi OS (64-bit, Lite or Desktop)
- LAN cable on the Pi (eth0) for internet / HA connection
- Wi-Fi interface (wlan0) used as hotspot for the GGS Controller
- Home Assistant on another device in the local network

> **Important:** SpiderBridge and the hotspot must run on the **same device** (the Pi).
> The Pi connects to your home network via Ethernet (eth0), opens a Wi-Fi hotspot on wlan0,
> and the GGS Controller connects to that hotspot — not to your regular home Wi-Fi.
> This is what allows the Pi to intercept the controller's MQTT traffic.

---

## First Connection

After installation, connect the GGS Controller to your configured Wi-Fi SSID. The MAC address is auto-detected on first connect and saved to `config.yaml`. The log will show:

```
┌─────────────────────────────────────────────┐
│  🕷  SpiderBridge — Gerät erkannt           │
│  MAC: 7C2C67F03DAC                          │
│  ID:  Spider Farmer GGS                     │
└─────────────────────────────────────────────┘
```

Watch logs:
```bash
sudo pm2 logs sf-proxy
```

---

## Home Assistant Setup

**Settings → Devices & Services → MQTT → Configure:**

| Field    | Value                                      |
|----------|--------------------------------------------|
| Broker   | Pi IP address (eth0, e.g. `192.168.1.100`) |
| Port     | `1883`                                     |
| Username | *(leave empty)*                            |
| Password | *(leave empty)*                            |

All entities appear automatically via MQTT Discovery under one device.

### Available Entities

| Type   | Entities                                                         |
|--------|------------------------------------------------------------------|
| Sensor | Air Temperature, Humidity, VPD                                   |
| Sensor | Soil Temperature / Humidity / EC (average + per sensor)          |
| Light  | Light 1 + Light 2 (on/off, brightness, mode: Manual/Timer, PPFD) |
| Fan    | Fan Exhaust (on/off + speed 0–100%)                              |
| Fan    | Fan Circulation (on/off + speed 0–10)                            |
| Switch | Heater, Humidifier, Dehumidifier                                 |
| Switch | Outlet 1–10                                                      |

Soil sensors are auto-discovered with their hardware ID on first connect.

---

## Managing Services

```bash
sudo pm2 list                    # Status overview
sudo pm2 logs sf-proxy           # Live proxy log
sudo pm2 logs sf-discovery       # Discovery publisher log
sudo pm2 restart sf-proxy        # Restart proxy
sudo pm2 restart sf-discovery    # Restart discovery
```

```bash
sudo bash /opt/spiderfarmer-bridge/start.sh   # Start all services
sudo bash /opt/spiderfarmer-bridge/stop.sh    # Stop all services
```

```bash
mosquitto_sub -h localhost -p 1883 -t 'spiderfarmer/#' -v   # Watch all MQTT topics
```

---

## Update

```bash
sudo git -C /opt/spiderfarmer-bridge pull
sudo pm2 restart sf-proxy sf-discovery
```

---

## Troubleshooting

**Controller does not connect to hotspot**
- GGS Controller supports 2.4 GHz only
- Check: `nmcli con show SF-Bridge-Hotspot | grep band`

**No data in Home Assistant**
- Check MQTT connection in HA
- Watch proxy log: `sudo pm2 logs sf-proxy`
- Verify MQTT topics: `mosquitto_sub -h localhost -p 1883 -t 'spiderfarmer/#' -v`

**Entities show as unavailable**
- Accessories (heater, humidifier, etc.) only appear after the controller reports their state
- Restart discovery: `sudo pm2 restart sf-discovery`

---

## Project Structure

```
spiderfarmer-bridge/
├── proxy/          # MQTT parser, normalizer, command handler, MITM proxy
├── ha/             # HA Discovery payloads and publisher service
├── config/         # config.yaml, mosquitto.conf
├── setup/          # bootstrap.sh, install.sh, wizard.sh, hotspot.sh
├── certs/          # TLS certificates
├── tests/          # Unit tests (pytest)
├── ecosystem.config.js
├── start.sh / stop.sh / update.sh
├── main_proxy.py
└── main_discovery.py
```

---

## Tests

```bash
cd /opt/spiderfarmer-bridge
.venv/bin/pytest tests/ -v
```
