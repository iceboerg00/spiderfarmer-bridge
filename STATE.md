# STATE

Last updated: 2026-04-18

## Status: Running on Pi — core features working

## Done
- Project scaffold
- MQTT parser (TDD, 10 tests)
- Normalizer (TDD, 13 tests)
- Command translator (TDD, 15 tests)
- HA Discovery builders (TDD, 7 tests)
- MITM Proxy (mitm_proxy.py + main_proxy.py)
- Discovery Publisher (ha/publisher.py + main_discovery.py)
- Mosquitto config
- Hotspot setup script
- Install script
- PM2 process management (replaced systemd for sf-proxy + sf-discovery)
- Auto-detect MAC from first CONNECT packet
- Pi deployed and running (device: 7C2C67F03DAC / ggs_1)
- Graceful SIGTERM shutdown (no more coroutine GeneratorExit errors)

## Entities in HA
- Air: Temperature, Humidity, VPD
- Light 1 + Light 2: on/off, brightness, mode (Manual/Timer, PPFD)
- Fan Exhaust: on/off, speed 0–100%
- Fan Circulation: on/off, speed 0–10
- Outlets 1–10: on/off switches
- Soil sensors (3x): Temperature, Humidity, EC per sensor + averages
- Heater / Humidifier / Dehumidifier: on/off

## Known limitations
- ShakeLevel (fan oscillation) not controllable via MQTT inject — device processes command but hardware doesn't respond; works only via BT or SF cloud
- Light 2 only visible if a second light is physically connected
- Server overrides injected commands periodically (intercept logic in place but not yet tested for non-shake fields)

## Open
- Licht-Timer / Schedule entity
- Alarm-Sensor (alarmLast in getDevSta)
- Outlet-Scheduling
