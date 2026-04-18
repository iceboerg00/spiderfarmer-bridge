#!/usr/bin/env bash
set -euo pipefail

echo "[start] Starte Spider Farmer Bridge..."
systemctl start mosquitto
systemctl start sf-proxy
systemctl start sf-discovery
echo "[start] Alle Services gestartet."
systemctl status sf-proxy sf-discovery --no-pager -l
