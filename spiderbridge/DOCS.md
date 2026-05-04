# SpiderBridge

Connects the Spider Farmer GGS Controller to Home Assistant — no cloud required, no separate device needed.

SpiderBridge creates a Wi-Fi hotspot on your Raspberry Pi, intercepts the encrypted MQTT traffic from the GGS Controller, and publishes all sensor data and device states directly to Home Assistant. The official Spider Farmer app continues to work in parallel.

## Requirements

- Raspberry Pi with Wi-Fi (wlan0) for the hotspot
- **LAN cable (eth0) is mandatory** — Wi-Fi is fully used by the hotspot, so Ethernet is the only connection to your home network

## Setup

1. Configure the add-on options (see below)
2. Start the add-on
3. **Restart Home Assistant Core** — Settings → System → Restart
4. Go to **Settings → Devices & Services → Add Integration → SpiderBridge**
5. Click **Add** — no further configuration needed
6. Connect the GGS Controller to the configured Wi-Fi SSID

On first connect, the GGS Controller is auto-detected. All entities appear automatically under one device.

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `hotspot_enabled` | `true` | Enable Wi-Fi hotspot on wlan0 |
| `ssid` | `SF-Bridge` | Wi-Fi network name for the GGS Controller |
| `password` | `changeme123` | Wi-Fi password — **change this before use** |
| `channel` | `6` | 2.4 GHz channel (1–11, GGS Controller is 2.4 GHz only) |
| `hotspot_ip` | `192.168.10.1` | Gateway IP of the hotspot |

The HA device name is hardcoded to `GGS` so entity IDs are consistent (`light.ggs_light_1`, `fan.ggs_fan_circulation`, …). Required for the bundled Lovelace card to discover them.

## Available Entities

| Type | Entities |
|------|----------|
| Sensor | Air Temperature, Humidity, VPD, CO₂, PPFD |
| Sensor | Soil Temperature / Humidity / EC (average + per sensor) |
| Light | Light 1 + Light 2 (on/off, brightness, mode) |
| Fan | Fan Exhaust (on/off + speed 0–100%) |
| Fan | Fan Circulation (on/off + speed 0–10) |
| Switch | Heater, Humidifier, Dehumidifier |
| Switch | Outlet 1–10 |

Soil sensors are auto-discovered by hardware ID on first connect.

Plus mode-specific settings as their own entities — schedule brightness, PPFD target, fan cycle run-time, environment submode, etc. Every setting available in the SF App is also available in HA.

## Lovelace Card

The add-on bundles a custom Lovelace card (tabs per device + mode dropdown + matching settings) and registers it as a Lovelace resource on first start. After the add-on starts and Home Assistant Core has been restarted:

1. Hard-refresh your browser (Ctrl+F5).
2. Edit a dashboard → "+ Add Card" → search "Spider Farmer".

```yaml
type: custom:ggs-card
```

## Hotspot Toggle

Set `hotspot_enabled: false` if your GGS Controller connects via an existing router. The MQTT proxy continues to intercept traffic on port 8883 — only the built-in hotspot is disabled.

## Troubleshooting

**Controller does not connect**
- GGS Controller supports 2.4 GHz only — use channels 1–11
- Check add-on log for `wlan0: AP-ENABLED`

**Entities show as unavailable**
- Accessories (heater, humidifier, etc.) only appear after the controller reports their state for the first time
- Restart the add-on to trigger re-discovery

**Integration not showing after update**
- Restart Home Assistant Core after each add-on update — the add-on installs the integration on every start, a Core restart is needed to pick up changes

## Notes

- The official Spider Farmer app continues to work in parallel — SpiderBridge is transparent to the cloud
- Source code: [github.com/iceboerg00/spiderfarmer-bridge](https://github.com/iceboerg00/spiderfarmer-bridge)
