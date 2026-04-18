# DEPLOYMENT

## Prerequisites
- Raspberry Pi 4 with Raspberry Pi OS (64-bit)
- LAN cable connected (eth0)
- Python 3.9+, git installed

## Quick Install
```bash
git clone <repo> /opt/spiderfarmer-bridge
cd /opt/spiderfarmer-bridge
# Edit config/config.yaml (hotspot SSID/password, HA credentials)
sudo bash setup/install.sh
sudo systemctl start sf-proxy sf-discovery
```

## First Connection
1. On GGS Controller: connect to Wi-Fi SSID from config.yaml
2. Watch logs: `journalctl -fu sf-proxy`
3. Note the client_id in "Session created" log line
4. Update `config.yaml` devices[0].mac with the real MAC
5. Restart: `systemctl restart sf-proxy sf-discovery`

## HA MQTT Integration
In Home Assistant → Settings → Devices & Services → MQTT:
- Broker: Pi IP address (eth0)
- Port: 1883
- Username: ha_user
- Password: (set in config.yaml as ha_mqtt_password)

## Update
```bash
cd /opt/spiderfarmer-bridge
git pull
systemctl restart sf-proxy sf-discovery
```

## Logs
```bash
journalctl -fu sf-proxy        # proxy logs
journalctl -fu sf-discovery    # discovery logs
journalctl -fu mosquitto       # broker logs
```
