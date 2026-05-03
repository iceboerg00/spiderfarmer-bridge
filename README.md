<p align="center">
  <img src="logo.png" alt="SpiderBridge Logo" width="400"/>
</p>

Local bridge zwischen dem Spider Farmer GGS Controller und Home Assistant via MQTT Discovery.

Ein Raspberry Pi macht ein Wi-Fi-Hotspot für den GGS Controller, fängt den verschlüsselten MQTT-Traffic ab, normalisiert die Daten und stellt sie Home Assistant bereit. Die offizielle Spider Farmer App und die Cloud funktionieren parallel weiter.

```
GGS Controller
     │  Wi-Fi (Hotspot vom Pi)
     ▼
Raspberry Pi ──── TLS MITM Proxy :8883
     │                      │
     │  eth0 (LAN)      Mosquitto :1883
     │                      │
     ▼                      ▼
  SF Cloud            Home Assistant
  (App läuft          (Entities werden
   weiter)             auto-discovered)
```

---

## Was du bekommst

Sobald der GGS Controller verbunden ist, tauchen automatisch Entitäten in HA auf — abhängig davon was am Controller hängt:

| Typ | Entitäten |
|------|----------|
| Sensoren | Lufttemperatur, Luftfeuchte, VPD, CO₂, PPFD |
| Sensoren | Boden-Temperatur / -Feuchte / EC (Durchschnitt + pro Sensor) |
| Light | Light 1, Light 2 (an/aus, Helligkeit, Modi: Manual/Schedule/PPFD) |
| Fan | Fan Exhaust (an/aus + Geschwindigkeit 0-100 %) |
| Fan | Fan Circulation (an/aus + Geschwindigkeit 0-10) |
| Switch | Heater, Humidifier, Dehumidifier |
| Switch | Outlet 1-10 (je nachdem welche Power Strip dranhängt) |

Plus: jede Mode-spezifische Einstellung als eigene Sub-Device-Entität (Schedule-Brightness, PPFD-Target, Fan-Cycle-Run-Time, Environment-Submode, …) — die SF App hat keine Einstellung, die nicht auch in HA verfügbar ist.

---

## Lovelace Card

Custom HA-Karte die SF-App-mäßig pro Gerät einen Tab zeigt mit Mode-Dropdown und passenden Settings darunter:

<p align="center">
  <img src="docs/ggs-card.png" alt="Spider Farmer GGS Card screenshot" width="900"/>
</p>

Drei Wege zur Karte (siehe **[Karte installieren](spiderbridge/frontend/README.md)** für die Detailanleitung):

- **HA Addon (Option A unten):** Karte installiert sich automatisch mit dem Addon. Keine Klicks extra.
- **HACS:** Repository als Frontend-Custom-Repo hinzufügen, Spider Farmer GGS Card installieren.
- **Manuell:** `npm run build`, Datei kopieren, Resource registrieren.

Im Dashboard:
```yaml
type: custom:ggs-card
```

---

## Welche Hardware brauche ich?

| Bauteil | Was es tut |
|---|---|
| Raspberry Pi mit WiFi (Pi 3, Pi 4, Pi 5, Zero 2 W) | Läuft als Bridge zwischen Controller und HA |
| LAN-Kabel | **Pflicht** — der Pi muss per Kabel im Heimnetz hängen, weil das WiFi-Modul vollständig vom Hotspot benutzt wird |
| Spider Farmer GGS Controller | Das Gerät dass du steuern willst (CB, PS5, PS10 oder LC) |
| Home Assistant | Auf demselben oder einem anderen Gerät im Heimnetz |

Es gibt **zwei Wege** den Pi einzurichten:

- **Option A — Pi läuft Home Assistant OS** und SpiderBridge ist ein Addon. Empfohlen für die meisten User. Pi und HA sind dasselbe Gerät.
- **Option B — Pi läuft Raspberry Pi OS** mit SpiderBridge als Standalone-Service. HA läuft separat (zweiter Pi, NUC, VM, was auch immer). Für die "klassische" Setup-Variante.

Wähl eine — der Rest der Anleitung ist getrennt nach Option.

---

## Option A — HA-Addon Setup (empfohlen)

> **Vorraussetzung:** Du hast bereits Home Assistant OS auf dem Pi installiert. Falls noch nicht — siehe https://www.home-assistant.io/installation/raspberrypi für die Erstinstallation, dann hier weitermachen.

> **Stelle sicher:** Pi ist per **LAN-Kabel** am Router. Die WLAN-Schnittstelle wird gleich für den Hotspot verwendet, also brauchst du Kabel-Internet.

### Schritt 1 — Repository in HA hinzufügen

1. **Home Assistant** im Browser öffnen.
2. Links unten auf dein Profil-Icon klicken → sicherstellen dass **"Advanced Mode"** an ist (sonst siehst du das Add-on Store nicht voll).
3. Links: **Settings** → **Add-ons** → unten rechts auf **"Add-on Store"** klicken.
4. Oben rechts auf das **⋮ (drei Punkte)** → **"Repositories"**.
5. Im Pop-up dieses URL eintragen: `https://github.com/iceboerg00/spiderfarmer-bridge`
6. **Add** klicken → **Close**.

### Schritt 2 — Addon installieren

1. Im Add-on Store nach unten scrollen → **"SpiderBridge Add-ons"** Bereich → **SpiderBridge** klicken.
2. **Install** klicken (kann 1-2 Minuten dauern, der Pi baut die Karte mit).

### Schritt 3 — Konfigurieren

Auf der Addon-Seite den Tab **Configuration** öffnen. Du siehst Felder wie unten — gib was passt ein:

| Feld | Was eintragen |
|---|---|
| `ssid` | Name des WLANs für den GGS Controller, frei wählbar (z.B. `GGS-Tent`) |
| `password` | WLAN-Passwort, **mindestens 8 Zeichen** (z.B. `SuperSafe123`) |
| `channel` | `6` ist eine sichere Wahl (ein Zahl von 1 bis 11) |
| `hotspot_ip` | `192.168.10.1` lassen, falls dieses Subnetz schon im Heimnetz vergeben ist auf etwas anderes ändern |
| `device_name` | Egal, z.B. `GGS Tent`. Wird der Name in HA. |
| `hotspot_enabled` | `true` lassen (Pi macht den Hotspot selbst — empfohlen) |

**Save** klicken (oben rechts).

### Schritt 4 — Addon starten

1. Tab **Info** öffnen → **"Start"** klicken.
2. **"Watchdog"** und **"Start on boot"** aktivieren (damit's nach Neustart automatisch wieder läuft).
3. Tab **Log** öffnen — du solltest Zeilen sehen wie `Hotspot enabled`, `Proxy listening on 0.0.0.0:8883`, etc. Falls Errors auftauchen, siehe [Troubleshooting](#troubleshooting).

### Schritt 5 — Home Assistant Core neustarten

**Settings → System → Restart** → **Restart Home Assistant Core**.

Das ist nötig damit HA die neue SpiderBridge-Integration mitkriegt.

### Schritt 6 — Integration aktivieren

1. **Settings → Devices & services**.
2. Unten rechts **+ Add Integration** → ins Suchfeld **"SpiderBridge"** tippen → klicken.
3. Ein einziger Klick auf **Submit** — keine weitere Eingabe nötig.

### Schritt 7 — GGS Controller verbinden

Am GGS Controller in der Spider Farmer App das Wi-Fi auf das in Schritt 3 angelegte Netz umstellen (SSID + Passwort dass du da eingegeben hast). Beim ersten Verbinden wird die MAC automatisch erkannt.

In den Addon-Logs solltest du eine Zeile wie diese sehen:

```
🕷  SpiderBridge — Gerät erkannt
   MAC: 7C2C67F03DAC
   ID:  GGS Tent
```

Ab diesem Moment tauchen die Entitäten in HA auf — meist innerhalb von 10-20 Sekunden.

### Schritt 8 — Karte aufs Dashboard

1. Browser **Strg+F5** (auf Mac: Cmd+Shift+R) damit HA die neu installierte Karte lädt.
2. Dashboard öffnen → **Edit Dashboard** → **+ Add Card** → "Spider Farmer" suchen → fertig.

---

## Option B — Standalone Pi mit Raspberry Pi OS

> **Vorraussetzung:** Du hast Raspberry Pi OS (64-bit) auf dem Pi installiert und SSH-Zugriff. Falls noch nicht — https://www.raspberrypi.com/software/ für den Imager. SSH einschalten in den Imager-Optionen oder durch eine leere `ssh`-Datei auf der SD-Karte.

> **Stelle sicher:** Pi ist per **LAN-Kabel** am Router. Genauso wie Option A.

### Schritt 1 — Per SSH auf den Pi

Auf deinem Hauptrechner ein Terminal öffnen:

```bash
ssh pi@<IP-des-Pi>
```

(IP findest du im Router oder mit `nmap`. Standard-User ist meistens `pi` oder der Name den du im Imager gesetzt hast.)

### Schritt 2 — One-Line-Installer ausführen

Auf dem Pi (im SSH-Terminal):

```bash
curl -sSL https://raw.githubusercontent.com/iceboerg00/spiderfarmer-bridge/master/setup/bootstrap.sh | sudo bash
```

Der Installer:
1. Klont das Repo nach `/opt/spiderfarmer-bridge`
2. Startet einen Setup-Wizard. Dort wirst du gefragt:
   - **SSID** — Name des WLANs für den GGS Controller (z.B. `GGS-Tent`)
   - **Passwort** — mindestens 8 Zeichen
   - **Gerätename** — kannst "GGS" lassen oder anpassen
3. Mosquitto-Broker, Python-venv, TLS-Zertifikate, pm2-Services (`sf-proxy`, `sf-discovery`) werden eingerichtet.
4. WLAN-Hotspot wird konfiguriert (mit den Stabilitäts-Tweaks die der GGS Controller braucht).

Das dauert 3-5 Minuten. Wenn fertig, sollte `sudo pm2 status` zwei Services online zeigen.

### Schritt 3 — Home Assistant mit Pi verbinden

Auf deinem HA-Gerät:

1. **Settings → Devices & services**.
2. Falls **MQTT** noch nicht eingerichtet: **+ Add Integration** → MQTT → klicken.
3. Im Konfigurations-Pop-up:
   - **Broker:** IP-Adresse des Pi (Ethernet-Adresse, z.B. `192.168.1.100`)
   - **Port:** `1883`
   - **Username/Password:** leer lassen
4. **Submit**.

Falls MQTT schon eingerichtet ist und auf einen anderen Broker zeigt: zwei Broker gleichzeitig sind möglich, oder du setzt den Pi-Broker als zusätzlichen via YAML-Config in `configuration.yaml`. Detail-Variante: siehe HA MQTT-Docs.

### Schritt 4 — GGS Controller verbinden

In der Spider Farmer App das Wi-Fi des Controllers aufs neu erstellte Netz umstellen (SSID/Passwort vom Wizard).

In den Logs auf dem Pi solltest du sehen:

```bash
sudo pm2 logs sf-proxy --lines 50
```

Eine Zeile wie `🕷  SpiderBridge — Gerät erkannt   MAC: ...` zeigt dass alles passt.

In HA tauchen ein paar Sekunden später die Entitäten unter dem `device_name` auf, den du im Wizard gesetzt hast.

### Schritt 5 — Karte aufs Dashboard

Bei Option B installiert sich die Karte **nicht automatisch** — du brauchst HACS oder den manuellen Weg. Siehe **[Karte installieren](spiderbridge/frontend/README.md)** Option B oder C.

---

## Updates einspielen

### Option A (Addon)

1. **Settings → Add-ons → SpiderBridge** → falls "Update available" oben steht, **Update** klicken.
2. Addon **Restart** klicken.
3. **Strg+F5** im Browser (Karte ist evtl. mit aktualisiert).

### Option B (Standalone)

```bash
sudo git -C /opt/spiderfarmer-bridge pull
sudo pm2 restart sf-proxy sf-discovery
```

Danach für die Karte: HACS → "Spider Farmer GGS Card" → Update, oder manuell `npm run build` + Datei kopieren.

---

## Troubleshooting

### Controller verbindet sich nicht mit dem Hotspot
- Der GGS Controller kann nur 2.4-GHz-WLAN — Channel zwischen 1 und 11 nutzen.
- Option A: im Addon-Log nach `AP-ENABLED` schauen.
- Option B: `nmcli con show SF-Bridge-Hotspot | grep band`. Sicherstellen dass `802-11-wireless.powersave` auf `2` (disabled) steht — sonst dropt der GGS Controller täglich.

### Keine Daten in Home Assistant
- Option A: Addon-Log auf `Proxy listening on 0.0.0.0:8883` checken.
- Option B: `sudo pm2 logs sf-proxy --lines 100`.
- MQTT-Topics manuell anschauen:
  ```bash
  mosquitto_sub -h <pi-ip> -p 1883 -t 'spiderfarmer/#' -v
  ```

### HA-Outlet schaltet PS5/PS10 nicht
- Der Proxy muss erst einmal einen Cloud→Device-Befehl gesehen haben, um den Topic-Prefix der Power Strip zu lernen. Lösung: einmal kurz in der SF App eine Steckdose schalten — danach merkt sich der Proxy den Prefix für die ganze Session.
- `sudo pm2 logs sf-proxy | grep "DOWN topic prefix"` — sobald die Zeile `DOWN topic prefix learned: PS (was CB)` auftaucht, läuft's.

### Entitäten als "unavailable"
- Heater/Humidifier/Dehumidifier erscheinen erst nachdem der Controller ihren Status meldet.
- Option A: Addon **Restart**.
- Option B: `sudo pm2 restart sf-discovery`.

### Karte erscheint nicht unter "+ Add Card"
- Browser hart neu laden — **Strg+F5**.
- HA → Settings → Dashboards → ⋮ → **Resources** → prüfen ob `/local/ggs-card.js` als JavaScript Module registriert ist. Falls nicht: manuell hinzufügen (URL `/local/ggs-card.js`, Type "JavaScript Module").

### Integration weg nach Addon-Update (Option A)
- Nach jedem Addon-Update das die Integration mitupdates: **Settings → System → Restart Home Assistant Core**.

---

## Pro-Tipps (Option B)

Services werden mit **pm2** verwaltet, nicht systemd:

```bash
sudo pm2 status                       # Service-Status
sudo pm2 logs sf-proxy                # Live-Log
sudo pm2 logs sf-proxy --lines 200    # Letzte 200 Zeilen
sudo pm2 restart sf-proxy             # Proxy neu starten
sudo pm2 restart sf-discovery         # Discovery-Service neu starten
```

Live alle MQTT-Topics ansehen die der Bridge published:

```bash
mosquitto_sub -h localhost -p 1883 -t 'spiderfarmer/#' -v
```

Tests laufen lassen (Option B):

```bash
cd /opt/spiderfarmer-bridge
.venv/bin/pytest tests/ -v
```

---

## Unterstützte Module

| Modul | Sensoren / Lichter | Outlets | HA-Steuerung |
|---|---|---|---|
| Control Box (CB) | Air, Soil, CO₂, PPFD, Lichter, Lüfter, Klima-Zubehör | — | voll |
| Power Strip 5 (PS5) | Air-Sensoren, Lichter, Blower/Fan | 5 | voll |
| Power Strip 10 (PS10) | Air-Sensoren, Lichter, Blower/Fan | 10 | voll |
| Light Controller (LC) | 2 Light-Channels mit Brightness, Modus, PPFD | — | teilweise |

Mehrere Module gleichzeitig am selben Controller laufen lassen geht — Entitäten werden für jedes auto-discovered.

---

## Projekt-Struktur

```
spiderfarmer-bridge/
├── proxy/                 # MQTT parser, normalizer, command handler, MITM proxy
├── ha/                    # HA Discovery payloads + publisher
├── config/                # config.yaml, mosquitto.conf
├── setup/                 # bootstrap.sh, install.sh, wizard.sh, hotspot.sh
├── certs/                 # TLS-Zertifikate
├── tests/                 # Backend-Tests (pytest)
├── docs/                  # README-Assets (Screenshot, etc.)
├── spiderbridge/          # HA Add-on (Option A)
│   ├── config.yaml
│   ├── Dockerfile         # Multi-Stage build mit Frontend
│   ├── app/               # Python-Code für den Container
│   ├── frontend/          # Lovelace Card (TypeScript + Lit)
│   ├── integration/       # HA Custom Integration (auto-installed by addon)
│   └── rootfs/            # s6 Service-Scripts + Auto-Install der Karte
├── hacs.json              # HACS Frontend-Repo Metadata
└── repository.yaml        # HA Custom-Repository Metadata
```
