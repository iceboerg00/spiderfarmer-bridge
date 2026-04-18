# TODO

## Done
- [x] Deploy to Pi
- [x] PM2 setup + autostart on reboot
- [x] Verify TLS MITM succeeds
- [x] Fill in controller MAC + UID from logs
- [x] Verify entities appear in HA
- [x] Test write commands (fan, light, outlets)
- [x] Fix graceful shutdown (SIGTERM)

## Optional features
- [ ] Licht-Timer: expose startTime/fadeTime/ppfdPeriod from light config as HA entities
- [ ] Alarm-Sensor: expose alarmLast (devType/alarmType) as HA binary sensor
- [ ] Outlet-Scheduling: timer support for outlets beyond simple on/off
- [ ] Clean up override intercept code if not needed for other fields
