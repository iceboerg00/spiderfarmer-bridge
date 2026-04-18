#!/usr/bin/env bash
set -euo pipefail

echo "[stop] Stoppe Spider Farmer Bridge..."
systemctl stop sf-proxy sf-discovery
echo "[stop] Services gestoppt."
