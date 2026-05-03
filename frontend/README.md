# Spider Farmer GGS Card

Custom Home Assistant Lovelace card for the SpiderBridge GGS controller.
Drop one card on your dashboard, get tabbed control + mode-dependent
settings for Light 1, Light 2, Fan Circulation, and Fan Exhaust.

## Install via HACS

1. In HACS → ⋮ → **Custom repositories** → add this repo's URL with
   category **Frontend**.
2. Install **Spider Farmer GGS Card** from HACS.
3. HA → Settings → Dashboards → ⋮ → **Resources** → confirm
   `/hacsfiles/spiderfarmer-bridge/ggs-card.js` is registered as
   `JavaScript Module`. (HACS adds it automatically on most setups.)
4. Edit a dashboard → "+ Add Card" → search for "Spider Farmer GGS"
   or paste:

   ```yaml
   type: custom:ggs-card
   ```

## Configuration

The card auto-discovers `light.ggs_*` and `fan.ggs_*` entities. No
configuration is required for single-controller setups.

| Option | Type | Default | Description |
|---|---|---|---|
| `device_id` | string | (auto) | Pin the card to a specific GGS device id (e.g. `ggs_1`). Useful when running multiple controllers. |

## Manual install (without HACS)

1. `npm install && npm run build` in `frontend/`.
2. Copy `frontend/dist/ggs-card.js` into your HA's `/config/www/`.
3. HA → Settings → Dashboards → ⋮ → **Resources** → Add Resource:
   - URL: `/local/ggs-card.js`
   - Resource type: `JavaScript Module`
4. Add the card to a dashboard as above.

## Development

```bash
cd frontend
npm install
npm test           # vitest
npm run dev        # rollup watch mode
npm run build      # production bundle
npm run lint
```

Tests live in `tests/`, mirroring `src/`.
