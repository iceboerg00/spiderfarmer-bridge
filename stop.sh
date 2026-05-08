#!/usr/bin/env bash
set -euo pipefail
# Symmetric to start.sh: stop the proxy/discovery services AND the
# Mosquitto broker. Previously stop.sh left mosquitto running, which
# was confusing because start.sh starts it.
pm2 stop sf-proxy sf-discovery
systemctl stop mosquitto
echo "[stop] Services stopped."
