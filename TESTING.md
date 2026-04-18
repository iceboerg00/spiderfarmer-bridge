# TESTING

## Unit Tests
```bash
cd /opt/spiderfarmer-bridge
.venv/bin/pytest tests/ -v
```
45 tests covering parser, normalizer, command handler, discovery.

## Mosquitto Smoke Test
```bash
# Subscribe (terminal 1)
mosquitto_sub -h 127.0.0.1 -p 1883 -u bridge -P bridge_secret -t 'spiderfarmer/#' -v

# Publish test (terminal 2)
mosquitto_pub -h 127.0.0.1 -p 1883 -u bridge -P bridge_secret \
  -t 'spiderfarmer/ggs_1/state/temperature' -m '24.5'
```

## Hotspot Test
```bash
# From another device connected to SF-Bridge Wi-Fi:
ping 192.168.10.1
nslookup sf.mqtt.spider-farmer.com  # should return 192.168.10.1
```

## MITM Connection Test
```bash
# Simulate a controller CONNECT (requires openssl):
openssl s_client -connect 192.168.10.1:8883 -servername sf.mqtt.spider-farmer.com
# Should complete TLS handshake. If "certificate verify failed" → cert pinning issue.
```

## HA Discovery Test
```bash
# After controller connects, check HA discovers entities:
mosquitto_sub -h 127.0.0.1 -p 1883 -u bridge -P bridge_secret \
  -t 'homeassistant/#' -v
```

## Write Path Test
```bash
mosquitto_pub -h 127.0.0.1 -p 1883 -u bridge -P bridge_secret \
  -t 'spiderfarmer/ggs_1/command/blower_speed/set' -m '5'
# Watch sf-proxy logs for "inject" message
```

## Cert Pinning Diagnosis
If you see "Upstream TLS failed" in sf-proxy logs:
- Cloud app still works (connection closed cleanly)
- See TROUBLESHOOTING.md for next steps
