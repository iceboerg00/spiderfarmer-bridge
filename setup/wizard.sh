#!/usr/bin/env bash
# Interactive config wizard — writes config/config.yaml
set -euo pipefail

# Redirect stdin to the controlling terminal — needed when the script
# is started via a pipe (curl | bash).
exec </dev/tty

INSTALL_DIR="${1:-/opt/spiderfarmer-bridge}"
CONFIG="$INSTALL_DIR/config/config.yaml"

echo ""
echo " _________      .__    .___          ___.         .__    .___              "
echo " /   _____/_____ |__| __| _/__________\_ |_________|__| __| _/ ____   ____  "
echo " \_____  \\\\____ \|  |/ __ |/ __ \_  __ \ __ \_  __ \  |/ __ | / ___\_/ __ \ "
echo " /        \  |_> >  / /_/ \  ___/|  | \/ \_\ \  | \/  / /_/ |/ /_/  >  ___/ "
echo "/_______  /   __/|__\____ |\___  >__|  |___  /__|  |__\____ |\___  / \___  >"
echo "        \/|__|           \/    \/          \/              \/_____/      \/  "
echo ""
echo "  Setup wizard"
echo "  --------------------------------------------------"
echo ""
echo "  Answer the questions below."
echo "  Empty input keeps the default value [in brackets]."
echo ""

# -- Hotspot ------------------------------------------------------------------
echo "-- Wi-Fi hotspot ----------------------------"
read -rp "  SSID (Wi-Fi name for the GGS Controller) [SF-Bridge]: " ssid
ssid="${ssid:-SF-Bridge}"

while true; do
  read -rsp "  Wi-Fi password (min. 8 characters) [changeme123]: " password
  echo ""
  password="${password:-changeme123}"
  if [[ ${#password} -ge 8 ]]; then
    break
  fi
  echo "  Error: password must be at least 8 characters."
done

read -rp "  Wi-Fi interface [wlan0]: " iface
iface="${iface:-wlan0}"

read -rp "  Hotspot IP address [192.168.10.1]: " hotspot_ip
hotspot_ip="${hotspot_ip:-192.168.10.1}"

echo ""

# -- Device -------------------------------------------------------------------
# Device name is hardcoded to "GGS" — keeps entity IDs consistent
# (light.ggs_light_1, fan.ggs_fan_exhaust, text.ggs_light_1_ppfd_start, ...)
# across all sub-devices. Multi-device setups can edit the name afterwards
# in config/config.yaml under devices[].friendly_name.
friendly_name="GGS"

# -- Internal password (no user input — random) -------------------------------
bridge_pass="$(tr -dc 'A-Za-z0-9' </dev/urandom | head -c 24 || true)"
if [[ -z "$bridge_pass" ]]; then
  bridge_pass="bridge_$(date +%s)"
fi

# -- Write the config ---------------------------------------------------------
mkdir -p "$(dirname "$CONFIG")"
cat > "$CONFIG" <<EOF
hotspot:
  ssid: "$ssid"
  password: "$password"
  interface: "$iface"
  ip: "$hotspot_ip"
  channel: 6

proxy:
  listen_host: "0.0.0.0"
  listen_port: 8883
  upstream_host: "sf.mqtt.spider-farmer.com"
  upstream_port: 8883
  cert_file: "certs/server.crt"
  key_file: "certs/server.key"

mosquitto:
  host: "127.0.0.1"
  port: 1883

devices:
  - mac: "AABBCCDDEEFF"   # auto-detected on first connect
    type: "CB"
    id: "ggs_1"
    uid: ""
    friendly_name: "$friendly_name"
EOF

echo "[ok] config written: $CONFIG"
echo ""
echo "  SSID:        $ssid"
echo "  Hotspot IP:  $hotspot_ip"
echo "  Interface:   $iface"
echo "  Device name: $friendly_name"
echo ""
