```
 _________      .__    .___          ___.         .__    .___
/   _____/_____ |__| __| _/__________\_ |_________|__| __| _/ ____   ____
\_____  \\____ \|  |/ __ |/ __ \_  __ \ __ \_  __ \  |/ __ | / ___\_/ __ \
/        \  |_> >  / /_/ \  ___/|  | \/ \_\ \  | \/  / /_/ |/ /_/  >  ___/
/_______  /   __/|__\____ |\___  >__|  |___  /__|  |__\____ |\___  / \___  >
        \/|__|           \/    \/          \/              \/_____/      \/
```

**Spider Farmer GGS Controller → Home Assistant** — local, no cloud required.

SpiderBridge runs on a Raspberry Pi and acts as a transparent MITM proxy between your GGS Controller and the Spider Farmer cloud. All sensor data is published to your local Home Assistant via MQTT Discovery. The official Spider Farmer app keeps working in parallel.

```
GGS Controller
      │  Wi-Fi (Pi hotspot)
      ▼
Raspberry Pi  ──  TLS MITM Proxy :8883  ──  SF Cloud (app still works)
      │
   Mosquitto :1883
      │
Home Assistant  (auto-discovered entities, full local control)
```

---

## One-line Install

```bash
curl -sSL https://raw.githubusercontent.com/iceboerg00/spiderfarmer-bridge/master/setup/bootstrap.sh | sudo bash
```

The setup wizard walks you through SSID, password, device name and HA MQTT credentials. Everything else is automatic.

**Requirements:**
- Raspberry Pi 4 — Raspberry Pi OS 64-bit (Lite recommended)
- Ethernet (eth0) for internet / HA connection
- Wi-Fi (wlan0) used as hotspot for the GGS Controller

---

## What you get in Home Assistant

| Entity | Details |
|--------|---------|
| 🌡 Air Temperature / Humidity / VPD | Live sensor data |
| 🌱 Soil Temperature / Humidity / EC | Per sensor + average (auto-discovered) |
| 💡 Light 1 / Light 2 | On/off, brightness 0–100%, mode (Manual/Timer, PPFD) |
| 💨 Fan Exhaust | On/off, speed 0–100% |
| 💨 Fan Circulation | On/off, speed 0–10 |
| 🔌 Outlets 1–10 | Individual on/off switches |
| 🌡 Heater / Humidifier / Dehumidifier | On/off |

Entities appear automatically the first time the controller connects — no manual configuration needed.

---

## First Connection

After install, connect the GGS Controller to your configured Wi-Fi SSID. The proxy auto-detects the MAC address on first connect and logs:

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

## Home Assistant MQTT Setup

**Settings → Devices & Services → MQTT → Configure:**

| Field | Value |
|-------|-------|
| Broker | Pi IP (eth0), e.g. `192.168.1.100` |
| Port | `1883` |
| Username / Password | *(leave empty)* |

---

## Managing Services

```bash
sudo pm2 list                  # Status
sudo pm2 logs sf-proxy         # Live proxy log
sudo pm2 logs sf-discovery     # Discovery publisher log
sudo pm2 restart sf-proxy      # Restart proxy
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

**Controller won't connect to hotspot**
- GGS Controller is 2.4 GHz only — check: `nmcli con show SF-Bridge-Hotspot | grep band`

**No data in Home Assistant**
- Verify MQTT broker connection in HA
- Check: `mosquitto_sub -h localhost -p 1883 -t 'spiderfarmer/#' -v`

**Entities show as unavailable**
- Accessories (heater, humidifier, etc.) only appear after the controller reports their state
- Restart sf-discovery: `sudo pm2 restart sf-discovery`

---

## Project Structure

```
spiderfarmer-bridge/
├── proxy/          # MITM proxy, MQTT parser, normalizer, command handler
├── ha/             # HA Discovery builder and publisher
├── config/         # config.yaml, mosquitto.conf
├── setup/          # bootstrap.sh, install.sh, wizard.sh, hotspot.sh
├── certs/          # TLS certificates
├── tests/          # Unit tests (pytest)
├── main_proxy.py
└── main_discovery.py
```

---

## Tests

```bash
cd /opt/spiderfarmer-bridge && .venv/bin/pytest tests/ -v
```
