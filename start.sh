#!/usr/bin/env bash
set -euo pipefail
INSTALL_DIR="/opt/spiderfarmer-bridge"
systemctl start mosquitto
pm2 start "$INSTALL_DIR/ecosystem.config.js"
pm2 list
