# Spider Farmer GGS Card

Custom Home Assistant Lovelace card for the SpiderBridge GGS Controller.
One card per dashboard with tabs for Light 1, Fan Circulation and
Fan Exhaust — mode dropdown plus all SF-App settings per mode.

---

## Install — pick ONE of the three options

> **Which one should I use?**
> - You run HA OS and use **the SpiderBridge addon**? → **Option A** (zero-click).
> - You use **HACS** and run the bridge manually on a Pi? → **Option B**.
> - No HACS, no addon, you want full manual control? → **Option C**.

---

### Option A — With the SpiderBridge HA addon (recommended, zero-click)

When you install (or update) the addon to v1.4+ the card is built and registered as a Lovelace resource automatically. You don't have to copy or register anything.

**Step by step:**

1. **Open HA** → ⚙️ **Settings** → **Add-ons** → **Add-on Store**
2. If SpiderBridge is already installed → click **Restart** on the SpiderBridge addon (this triggers the card auto-install)
3. If not installed yet: **⋮ (top right)** → **Repositories** → paste `https://github.com/iceboerg00/spiderfarmer-bridge` → **Add** → install SpiderBridge → **Start**
4. **Wait a minute** — the addon copies the card and registers it.
5. **Hard-refresh the browser tab with HA** — Windows: `Ctrl+F5`, Mac: `Cmd+Shift+R`. Required so HA picks up the new resource.
6. **HA → Settings → Dashboards** → open a dashboard → **Edit Dashboard** (pencil top right) → **+ Add Card** → search **"Spider Farmer"** → pick the card.

If the card doesn't show up under **+ Add Card**:
- Go to **Settings → Dashboards → ⋮ (top right) → Resources**.
- Check whether `/local/ggs-card.js` is listed as a **JavaScript Module**.
- If yes → hard-refresh again (Ctrl+F5).
- If no → click **+ Add Resource** → URL: `/local/ggs-card.js`, type: **JavaScript Module** → Save → hard-refresh.

---

### Option B — Via HACS (when the bridge isn't running as an addon)

If you installed the bridge manually on a Raspberry Pi (clone + pm2), HACS is the easiest way to get the card.

**Step by step:**

1. **HACS must be installed.** If not yet: https://hacs.xyz/docs/setup/download — follow the docs there.
2. Open **HA → HACS**.
3. Top right **⋮** → **Custom repositories**.
4. In the popup:
   - **Repository:** `https://github.com/iceboerg00/spiderfarmer-bridge`
   - **Type:** **Frontend**
   - Click **Add**.
5. Close the popup, reopen the HACS page, find **"Spider Farmer GGS Card"** in the list → click → bottom right **Download** → confirm version.
6. HACS says "You need to reload your browser" → press **Ctrl+F5**.
7. **HA → Settings → Dashboards** → open a dashboard → **Edit** → **+ Add Card** → search "Spider Farmer" → done.

If the card doesn't appear under "+ Add Card", run the same Resource check from Option A.

---

### Option C — Fully manual (for developers, or where neither addon nor HACS is an option)

You'll need Node.js on your machine to build the card.

**Step by step:**

1. **Install Node.js** (version 20 or newer). Download: https://nodejs.org/
2. **Clone the repo:**
   ```bash
   git clone https://github.com/iceboerg00/spiderfarmer-bridge
   cd spiderfarmer-bridge/spiderbridge/frontend
   ```
3. **Install dependencies + build the card:**
   ```bash
   npm install
   npm run build
   ```
   Output: `dist/ggs-card.js` (~50 kB).
4. **Copy the file to HA's `www/`** directory.
   - HA OS / Supervised: `/config/www/ggs-card.js` (over Samba share or the File Editor addon)
   - Docker: into the mounted config folder under `www/`
   - HA Core (Python venv): `~/.homeassistant/www/ggs-card.js`
5. **Register the resource in HA:**
   - HA → **Settings → Dashboards → ⋮ (top right) → Resources**
   - **+ Add Resource:**
     - **URL:** `/local/ggs-card.js`
     - **Resource type:** **JavaScript Module**
   - **Save**.
6. **Hard-refresh the browser** — Ctrl+F5 / Cmd+Shift+R.
7. **Edit a dashboard → "+ Add Card" → search "Spider Farmer"** → done.

---

## Adding the card to a dashboard

Once installed and the resource is registered, just add it as a card:

```yaml
type: custom:ggs-card
```

If you have a single GGS Controller, that's it. Multi-controller / hardware quirks? See **Configuration** below.

---

## Configuration

The card auto-discovers `light.ggs_*` and `fan.ggs_*` entities — no config required for single-controller setups.

When you add the card via **+ Add Card**, HA inserts a default YAML with sensible values (full-width layout, hardware-typical slider floors). You can edit any of these in the YAML editor.

| Option | Type | Default | What it does |
|---|---|---|---|
| `device_id` | string | (auto) | With multiple GGS controllers, pin the card to a specific one (e.g. `ggs_1`). |
| `layout_options.grid_columns` | number | `48` | Width in HA section-view columns (1-48). 48 = full width. |
| `layout_options.grid_rows` | number | `12` | Height in section-view rows (1-12 typical). |
| `layout_options.grid_min_columns` | number | `4` | Lower bound when dragging the resize handle. |
| `layout_options.grid_min_rows` | number | `3` | Lower bound for height. |
| `slider_min.light` | number | `11` | Slider minimum for Light (typical light-dimmer floor). |
| `slider_min.fan_circulation` | number | `10` | Minimum for Fan Circulation (= 1 speed level). |
| `slider_min.fan_exhaust` | number | `25` | Minimum for Fan Exhaust (typical mechanical floor). |

**Full example with every option:**

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

> **Note:** the `slider_min` defaults reflect typical SF GGS hardware. If your setup has different floors (e.g. a different exhaust fan that already spins at 15 %), adjust the values or set them to `0`.

---

## Using the card — what you'll see

- **Tabs at the top** — switch between Light 1, Fan Circulation, Fan Exhaust.
- **Status header** with an on/off toggle on the right.
- **Big slider** for brightness / speed.
- **Mode dropdown** (Manual / Schedule / PPFD for light, 8 modes for fan).
- **Settings underneath** swap automatically when you change the mode.
- For light there's also a **Temperature Protection** block at the bottom (always visible, applies in every mode).

---

## Updates

- **Option A (addon):** update the addon → the card updates automatically. Hard-refresh.
- **Option B (HACS):** HACS surfaces the update → install → hard-refresh.
- **Option C (manual):** `git pull` + `npm run build` + copy the file → hard-refresh.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| "+ Add Card" doesn't list "Spider Farmer GGS" | Resource registered? (Settings → Dashboards → Resources) Browser hard-refreshed? |
| Card shows "No GGS devices found" | Bridge running? Discovery completed? Check whether entities like `light.ggs_light_1` exist in HA. |
| Slider can't go fully to 0 % | Hardware floor. Set the matching `slider_min` in the card YAML to `0` (or a value that works for your hardware). |
| Mode dropdown changes but settings card doesn't swap | Hard-refresh. If still no fix, open browser devtools → console for errors. |

---

## Development

```bash
cd spiderbridge/frontend
npm install
npm test           # vitest
npm run dev        # rollup watch mode (live rebuild on source change)
npm run build      # production bundle → dist/ggs-card.js
npm run lint
```

Tests in `tests/`, mirroring the `src/` layout.

The addon's Dockerfile (`spiderbridge/Dockerfile`) does a multi-stage build that automatically runs `npm ci && npm run build` and bakes `ggs-card.js` into the addon image — no pre-built JS in git.
