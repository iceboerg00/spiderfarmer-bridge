# Spider Farmer GGS → Home Assistant Bridge

Local bridge for the Spider Farmer GGS Controller → Home Assistant via MQTT Discovery.

A Raspberry Pi 4 acts as a Wi-Fi hotspot for the GGS Controller. The Pi intercepts the MQTT/TLS traffic, normalizes the data, and publishes it to a local Mosquitto broker for Home Assistant. The official Spider Farmer app and cloud continue to work in parallel.

```
GGS Controller
     │ Wi-Fi (hotspot on Pi)
     ▼
Raspberry Pi 4 ──── TLS MITM Proxy :8883
     │                      │
     │ eth0 (LAN)       Mosquitto :1883
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
2. Run an interactive setup wizard (SSID, password, device name)
3. Configure Mosquitto, Python venv, TLS certificates, and systemd services
4. Set up the Wi-Fi hotspot

---

## Requirements

- Raspberry Pi 4 with Raspberry Pi OS (64-bit, Lite or Desktop)
- LAN cable on the Pi (eth0) for internet access
- Wi-Fi interface (wlan0) used as hotspot for the GGS Controller
- Home Assistant on another device in the local network

---

## First Connection

After installation:

1. **Start services:**
   ```bash
   sudo systemctl start sf-proxy sf-discovery
   ```

2. **Connect the GGS Controller** to the configured Wi-Fi network

3. **MAC address is auto-detected** — the proxy detects the controller's MAC on first connect and saves it to `config.yaml`. The log will show:
   ```
   AUTO-DETECT: MAC detected → AABBCCDDEEFF
   ```

4. **Watch logs:**
   ```bash
   journalctl -fu sf-proxy
   ```

---

## Home Assistant Setup

In Home Assistant → **Settings → Devices & Services → MQTT → Configure:**

| Field    | Value                                      |
|----------|--------------------------------------------|
| Broker   | Pi IP address (eth0, e.g. `192.168.1.100`) |
| Port     | `1883`                                     |
| Username | *(leave empty)*                            |
| Password | *(leave empty)*                            |

All entities appear automatically via MQTT Discovery under one device.

### Available Entities

| Type   | Entities                                                  |
|--------|-----------------------------------------------------------|
| Sensor | Temperature, Humidity, VPD                                |
| Sensor | Soil Temperature / Humidity / EC (average + per sensor)   |
| Light  | Light (on/off + brightness)                               |
| Fan    | Exhaust Fan (on/off + speed 0–100%)                       |
| Fan    | Circulation Fan (on/off + speed 0–10)                     |
| Switch | Heater, Humidifier, Dehumidifier                          |
| Switch | Outlet 1–4                                                |

Soil sensors are discovered automatically with their hardware ID when the controller first connects.

---

## Controls & Scripts

```bash
sudo bash /opt/spiderfarmer-bridge/start.sh   # Start all services
sudo bash /opt/spiderfarmer-bridge/stop.sh    # Stop all services
```

```bash
journalctl -fu sf-proxy        # Proxy logs (connections, MQTT data)
journalctl -fu sf-discovery    # HA Discovery publisher
journalctl -fu mosquitto       # MQTT broker
```

---

## Update

```bash
cd /opt/spiderfarmer-bridge
sudo git pull
sudo systemctl restart sf-proxy sf-discovery
```

---

## Troubleshooting

**Controller does not connect to hotspot**
- GGS Controller supports 2.4 GHz only
- Check: `nmcli con show SF-Bridge-Hotspot | grep band`

**No data in Home Assistant**
- Check MQTT connection in HA
- Watch proxy log: `journalctl -fu sf-proxy`
- Verify MQTT topics: `mosquitto_sub -h 127.0.0.1 -p 1883 -t 'spiderfarmer/#' -v`

**Outlet/heater entities always unknown**
- These accessories may not be connected to the controller
- They update automatically once the controller reports their state

---

## Project Structure

```
spiderfarmer-bridge/
├── proxy/              # MQTT parser, normalizer, command handler, MITM proxy
├── ha/                 # HA Discovery payloads and publisher service
├── config/             # config.yaml, mosquitto.conf
├── setup/              # bootstrap.sh, install.sh, wizard.sh, hotspot.sh
├── systemd/            # sf-proxy.service, sf-discovery.service
├── certs/              # TLS certificates
├── tests/              # Unit tests (pytest)
├── start.sh / stop.sh
├── main_proxy.py
└── main_discovery.py
```

---

## Tests

```bash
cd /opt/spiderfarmer-bridge
.venv/bin/pytest tests/ -v
```
