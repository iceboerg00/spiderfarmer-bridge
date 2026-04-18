# ARCHITECTURE

See full design doc: docs/superpowers/specs/2026-04-18-spiderfarmer-bridge-design.md

## Component Summary

| Component | File | Role |
|---|---|---|
| Config | proxy/config.py | Load config.yaml |
| MQTT Parser | proxy/mqtt_parser.py | Encode/decode raw MQTT packets |
| Normalizer | proxy/normalizer.py | SF topics → normalized topics |
| Command Handler | proxy/command_handler.py | HA commands → SF setConfigField |
| MITM Proxy | proxy/mitm_proxy.py | asyncio TLS MITM server |
| Discovery Builders | ha/discovery.py | Build HA discovery payloads |
| Discovery Publisher | ha/publisher.py | Monitor availability, publish discovery |
| Proxy Entry | main_proxy.py | Wire up and run proxy |
| Discovery Entry | main_discovery.py | Wire up and run discovery publisher |

## Data Flow
Controller → [TLS, Pi cert] → mitm_proxy.py → normalize → Mosquitto → HA
                                    ↓
                           [re-encrypt] → SF Cloud → Controller
