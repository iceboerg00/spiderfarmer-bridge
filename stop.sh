#!/usr/bin/env bash
set -euo pipefail
pm2 stop sf-proxy sf-discovery
echo "[stop] Services stopped."
