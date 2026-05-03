# Spider Farmer GGS Card

Custom Home Assistant Lovelace card für den SpiderBridge GGS Controller.
Eine Karte fürs Dashboard mit Tabs für Light 1, Fan Circulation und
Fan Exhaust — Mode-Dropdown + alle SF-App-Einstellungen pro Modus.

---

## Installation — du brauchst nur EINE der drei Optionen

> **Welche soll ich nehmen?**
> - Du hast HA OS und nutzt **das SpiderBridge Addon**? → **Option A** (zero-click).
> - Du nutzt **HACS** und betreibst die Bridge manuell auf einem Pi? → **Option B**.
> - Kein HACS, kein Addon, du willst alles selbst machen? → **Option C**.

---

### Option A — Mit dem SpiderBridge HA Addon (empfohlen, Null-Klick)

Wenn du das Addon installierst (oder bereits installiert hast und auf Version 1.4+ updatest), wird die Karte automatisch in HA eingebaut. Du musst **nichts** kopieren oder registrieren.

**Schritt für Schritt:**

1. **HA öffnen** → ⚙️ **Settings** → **Add-ons** → **Add-on Store**
2. Falls SpiderBridge schon installiert ist → bei **SpiderBridge** auf **"Restart"** klicken (das löst den Auto-Install der Karte aus)
3. Falls noch nicht installiert: **⋮ (oben rechts)** → **"Repositories"** → URL `https://github.com/iceboerg00/spiderfarmer-bridge` einfügen → **Add** → SpiderBridge installieren → **Start**
4. **Eine Minute warten** — das Addon kopiert die Karte und registriert sie automatisch.
5. **Browser-Tab mit HA hart neu laden** — auf Windows `Strg+F5`, auf Mac `Cmd+Shift+R`. Wichtig damit HA die neue Karte lädt.
6. **HA → Settings → Dashboards** → ein Dashboard öffnen → **"Edit Dashboard"** (Stift oben rechts) → **"+ Add Card"** → ins Suchfeld **"Spider Farmer"** tippen → Karte auswählen.

Falls die Karte unter "+ Add Card" nicht erscheint:
- Geh zu **Settings → Dashboards → ⋮ (oben rechts) → Resources**.
- Prüf ob `/local/ggs-card.js` als **JavaScript Module** in der Liste steht.
- Wenn ja → einfach Browser nochmal hart neu laden (Strg+F5).
- Wenn nein → klick **+ Add Resource** → URL: `/local/ggs-card.js`, Type: **JavaScript Module** → Save → Browser hart neu laden.

---

### Option B — Mit HACS (wenn die Bridge nicht als Addon läuft)

Wenn du die Bridge manuell auf einem Raspberry Pi installiert hast (clone + pm2), dann ist HACS der einfachste Weg an die Karte zu kommen.

**Schritt für Schritt:**

1. **HACS muss installiert sein.** Falls nicht: https://hacs.xyz/docs/setup/download — Anleitung dort folgen.
2. **HA → HACS** öffnen.
3. Oben rechts **⋮** → **"Custom repositories"** klicken.
4. Im Pop-up:
   - **Repository:** `https://github.com/iceboerg00/spiderfarmer-bridge`
   - **Type:** **Frontend**
   - Auf **"Add"** klicken.
5. Pop-up schließen, HACS-Seite erneut öffnen, in der Liste **"Spider Farmer GGS Card"** suchen → klicken → unten rechts **"Download"** klicken → Version bestätigen.
6. HACS sagt jetzt "You need to reload your browser" — **Strg+F5** drücken.
7. **HA → Settings → Dashboards** → Dashboard öffnen → **Edit** → **+ Add Card** → "Spider Farmer" suchen → fertig.

Falls die Karte beim "+ Add Card" nicht erscheint, gleicher Resource-Check wie unter Option A.

---

### Option C — Komplett manuell (für Entwickler oder wenn weder Addon noch HACS verfügbar)

Du brauchst Node.js auf deinem Rechner um die Karte selbst zu bauen.

**Schritt für Schritt:**

1. **Node.js installieren** (Version 20 oder neuer). Download: https://nodejs.org/
2. **Repo klonen:**
   ```bash
   git clone https://github.com/iceboerg00/spiderfarmer-bridge
   cd spiderfarmer-bridge/spiderbridge/frontend
   ```
3. **Abhängigkeiten installieren + Karte bauen:**
   ```bash
   npm install
   npm run build
   ```
   Resultat: Datei `dist/ggs-card.js` (ca. 50 kB).
4. **Datei nach HA kopieren** ins `www/`-Verzeichnis deiner HA-Config.
   - Bei HA OS / Supervised: `/config/www/ggs-card.js` (über Samba-Share oder File Editor Addon)
   - Bei Docker: in den gemounteten config-Ordner unter `www/`
   - Bei HA Core (Python venv): `~/.homeassistant/www/ggs-card.js`
5. **Resource in HA registrieren:**
   - HA → **Settings → Dashboards → ⋮ (oben rechts) → Resources**
   - **+ Add Resource**:
     - **URL:** `/local/ggs-card.js`
     - **Resource type:** **JavaScript Module**
   - **Save**.
6. **Browser hart neu laden** — Strg+F5 / Cmd+Shift+R.
7. **Dashboard editieren → "+ Add Card" → "Spider Farmer"** suchen → fertig.

---

## Karte aufs Dashboard

Nachdem sie installiert + die Resource registriert ist, einfach im Dashboard als Karte hinzufügen:

```yaml
type: custom:ggs-card
```

Wenn du nur einen GGS Controller hast war's das. Mehrere Controller / Hardware-Eigenheiten? Siehe **Konfiguration** unten.

---

## Konfiguration

Die Karte findet `light.ggs_*` und `fan.ggs_*` Entities automatisch — keine Config nötig wenn du einen Controller hast.

Wenn du die Karte über **"+ Add Card"** hinzufügst, schreibt HA automatisch eine Default-Config rein die schon sinnvolle Werte hat (Vollbreite, Hardware-typische Slider-Mindestwerte). Du kannst alle Felder direkt im YAML-Editor anpassen.

| Option | Typ | Default | Was es tut |
|---|---|---|---|
| `device_id` | string | (auto) | Bei mehreren GGS Controllern: bindet die Karte an einen bestimmten (z.B. `ggs_1`). |
| `layout_options.grid_columns` | number | `48` | Breite in HA-Section-View Spalten (1-48). 48 = volle Breite. |
| `layout_options.grid_rows` | number | `12` | Höhe in Section-View Reihen (1-12 typisch). |
| `layout_options.grid_min_columns` | number | `4` | Untergrenze beim Resize-Drag. |
| `layout_options.grid_min_rows` | number | `3` | Untergrenze für die Höhe. |
| `slider_min.light` | number | `11` | Slider-Mindestwert für Light (Light-Dimmer-Floor). |
| `slider_min.fan_circulation` | number | `10` | Mindestwert für Fan Circulation (= 1 Speed-Level). |
| `slider_min.fan_exhaust` | number | `25` | Mindestwert für Fan Exhaust (typische mechanische Mindestdrehzahl). |

**Vollständiges Beispiel mit allen Optionen:**

```yaml
type: custom:ggs-card
device_id: ggs_1
layout_options:
  grid_columns: 48
  grid_rows: 12
slider_min:
  light: 11
  fan_circulation: 10
  fan_exhaust: 25
```

> **Wichtig:** `slider_min`-Defaults orientieren sich an typischer SF-GGS-Hardware. Falls dein Setup andere Schwellen hat (z.B. ein anderer Abluftventilator fängt schon bei 15 % an zu drehen), Werte anpassen oder auf `0` setzen.

---

## Bedienung — was du in der Karte sehen wirst

- **Tabs oben** — Light 1, Fan Circulation, Fan Exhaust auswählen.
- **Status-Header** rechts mit Toggle-Schalter zum An/Aus-Schalten.
- **Großer Slider** für Helligkeit / Geschwindigkeit.
- **Mode-Dropdown** (Manual / Schedule / PPFD bei Light, 8 Modi bei Fan).
- **Settings darunter** wechseln automatisch je nach gewähltem Modus.
- Bei Light gibt's zusätzlich ganz unten **Temperature Protection** (immer sichtbar, gilt in jedem Modus).

---

## Update

- **Option A (Addon):** Addon updaten → Karte wird automatisch mitaktualisiert. Browser hart neu laden.
- **Option B (HACS):** HACS sagt dir wenn ein Update verfügbar ist → Update installieren → Browser hart neu laden.
- **Option C (manuell):** `git pull` + `npm run build` + Datei neu kopieren + Browser hart neu laden.

---

## Probleme?

| Symptom | Lösung |
|---|---|
| "+ Add Card" zeigt keine "Spider Farmer GGS"-Karte | Resource registriert? (Settings → Dashboards → Resources) Browser hart neu geladen? |
| Karte zeigt "No GGS devices found" | Bridge läuft? Discovery durchgelaufen? Schau ob Entitäten wie `light.ggs_light_1` in HA existieren. |
| Slider geht nicht ganz nach unten | Hardware-Mindestwert. Setze `slider_min` in der Karten-YAML auf den passenden Wert. |
| Mode-Dropdown ändert sich aber Settings-Karte tauscht nicht | Browser hart neu laden. Wenn das nicht hilft, mit dem Browser-Devtools nachschauen ob ein Fehler in der Konsole steht. |

---

## Entwicklung

```bash
cd spiderbridge/frontend
npm install
npm test           # vitest
npm run dev        # rollup watch mode (live-rebuild bei Quellcode-Änderung)
npm run build      # production bundle → dist/ggs-card.js
npm run lint
```

Tests in `tests/`, mirror der `src/` Struktur.

Die Addon-Dockerfile (`spiderbridge/Dockerfile`) macht einen Multi-Stage Build, der die Karte automatisch baut und ins Addon-Image bakt — kein vorgebautes JS-File im Repo.
