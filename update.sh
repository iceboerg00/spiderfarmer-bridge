#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR="/opt/spiderfarmer-bridge"
cd "$INSTALL_DIR"

echo "[update] Checking for updates..."
git fetch origin master

LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/master)

PULLED=0
if [[ "$LOCAL" != "$REMOTE" ]]; then
  echo "[update] New version available — pulling..."
  git pull --ff-only origin master
  PULLED=1
else
  echo "[update] Already at latest commit."
fi

# Always restart pm2 — previous runs that pulled but failed to restart
# would otherwise be stuck on stale code (LOCAL == REMOTE on the next
# run, early-exit, services never picked up the new files). Restarting
# unconditionally is cheap and idempotent.
echo "[update] Restarting services..."
if ! pm2 restart sf-proxy sf-discovery; then
  echo "[update] ERROR: pm2 restart failed."
  echo "[update] Try: sudo pm2 delete all && sudo pm2 start ecosystem.config.js && sudo pm2 save"
  exit 1
fi

if [[ "$PULLED" == "1" ]]; then
  echo "[update] Update complete (new code + services restarted)."
else
  echo "[update] Up-to-date — services restarted defensively."
fi
