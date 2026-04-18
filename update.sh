#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR="/opt/spiderfarmer-bridge"
cd "$INSTALL_DIR"

echo "[update] Checking for updates..."
git fetch origin master

LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/master)

if [[ "$LOCAL" == "$REMOTE" ]]; then
  echo "[update] Already up to date."
  exit 0
fi

echo "[update] New version available — updating..."
git pull --ff-only origin master

echo "[update] Restarting services..."
pm2 restart sf-proxy sf-discovery

echo "[update] Update complete."
