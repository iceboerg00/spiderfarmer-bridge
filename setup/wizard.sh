#!/usr/bin/env bash
# Interactive config wizard — writes config/config.yaml
set -euo pipefail

# Stdin auf Terminal umleiten — nötig wenn das Script per Pipe (curl | bash) gestartet wird
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
echo "  Setup-Assistent"
echo "  ──────────────────────────────────────────────────"
echo ""
echo "  Bitte die folgenden Fragen beantworten."
echo "  Leere Eingabe übernimmt den Standardwert [in Klammern]."
echo ""

# ── Hotspot ──────────────────────────────────────────────────────────────────
echo "── WLAN-Hotspot ────────────────────────────────"
read -rp "  SSID (WLAN-Name für GGS Controller) [SF-Bridge]: " ssid
ssid="${ssid:-SF-Bridge}"

while true; do
  read -rsp "  WLAN-Passwort (mind. 8 Zeichen) [changeme123]: " password
  echo ""
  password="${password:-changeme123}"
  if [[ ${#password} -ge 8 ]]; then
    break
  fi
  echo "  Fehler: Passwort muss mindestens 8 Zeichen haben."
done

read -rp "  WLAN-Interface [wlan0]: " iface
iface="${iface:-wlan0}"

read -rp "  Hotspot-IP-Adresse [192.168.10.1]: " hotspot_ip
hotspot_ip="${hotspot_ip:-192.168.10.1}"

echo ""

# ── Gerät ─────────────────────────────────────────────────────────────────────
echo "── GGS Controller ──────────────────────────────"
read -rp "  Gerätename in Home Assistant [Spider Farmer GGS]: " friendly_name
friendly_name="${friendly_name:-Spider Farmer GGS}"

echo ""

# ── Internes Passwort (kein User-Input nötig, zufällig generieren) ────────────
bridge_pass="$(tr -dc 'A-Za-z0-9' </dev/urandom | head -c 24 || true)"
if [[ -z "$bridge_pass" ]]; then
  bridge_pass="bridge_$(date +%s)"
fi

# ── Config schreiben ──────────────────────────────────────────────────────────
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
  - mac: "AABBCCDDEEFF"   # Wird beim ersten Verbinden automatisch erkannt
    type: "CB"
    id: "ggs_1"
    uid: ""
    friendly_name: "$friendly_name"
EOF

echo "✓ Konfiguration gespeichert: $CONFIG"
echo ""
echo "  SSID:        $ssid"
echo "  Hotspot-IP:  $hotspot_ip"
echo "  Interface:   $iface"
echo "  Gerätename:  $friendly_name"
echo ""
