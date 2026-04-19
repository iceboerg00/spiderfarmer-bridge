# SpiderBridge

Connects the Spider Farmer GGS Controller to Home Assistant via MQTT Discovery.

## Requirements

- Raspberry Pi with Wi-Fi (wlan0) for the hotspot
- LAN cable (eth0) for internet and HA connection

## Setup

1. Install and configure the add-on options
2. Start the add-on
3. In Home Assistant: **Settings → Devices & Services → MQTT → Configure**
   - Broker: IP address of this device (eth0)
   - Port: `1883`
   - Username/Password: leave empty
4. Connect the GGS Controller to the configured Wi-Fi SSID

## First Connection

On first connect the GGS Controller MAC is auto-detected and saved to `/data/devices.yaml`.
All entities appear automatically under one device in Home Assistant.

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `hotspot_enabled` | `true` | Enable Wi-Fi hotspot on wlan0 |
| `ssid` | `SF-Bridge` | SSID the GGS Controller connects to |
| `password` | `changeme123` | Wi-Fi password — **change this** |
| `channel` | `6` | 2.4 GHz channel (1–11) |
| `hotspot_ip` | `192.168.10.1` | Gateway IP of the hotspot |
| `device_name` | `Spider Farmer GGS` | Friendly name in Home Assistant |

## Notes

- The official Spider Farmer app continues to work in parallel
- Set `hotspot_enabled: false` if the hotspot is provided by an external router;
  the proxy still intercepts traffic on port 8883
