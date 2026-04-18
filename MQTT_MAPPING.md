# MQTT_MAPPING

## Spider Farmer Protocol

Topic format: `ggs/{device_type}/{mac}/{data_type}`

Known device types: CB, LC, PS5, PS10

### Observed Topics (fill in after first real connection)
| Topic | Description | Example Payload |
|---|---|---|
| ggs/{type}/{mac}/sensors | Environmental data | `{"temp":24.5,"humi":65,"vpd":1.1,"co2":800,"ppfd":600}` |
| ggs/{type}/{mac}/status | Full device state | `{"data":{"sensor":{...},"blower":{...},...}}` |
| ggs/{type}/{mac}/system | System info | `{"data":{"sys":{"ver":"...","upTime":...}}}` |
| ggs/{type}/{mac}/down | Cloud→device commands | `{"method":"setConfigField",...}` |

### Write Command Format
```json
{
  "method": "setConfigField",
  "params": { "keyPath": ["device", "blower"], "blower": { "mLevel": 5 } },
  "pid": "<mac>",
  "msgId": 1713456789000,
  "uid": "<uid>",
  "UTC": 1713456789
}
```

## Normalized Topics (local)
See design spec: docs/superpowers/specs/2026-04-18-spiderfarmer-bridge-design.md

## Field Aliases Observed
- Level: `mLevel` or `level`
- On/off: `mOnOff` or `on`

## Unknown/TBD
- [ ] Exact outlet count for this device
- [ ] Soil sensor presence
- [ ] TLS version / cipher suite accepted
