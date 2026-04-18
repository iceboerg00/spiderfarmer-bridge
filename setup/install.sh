#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR="/opt/spiderfarmer-bridge"
VENV="$INSTALL_DIR/.venv"

echo ""
echo "  ██████╗ ██████╗ ██╗██████╗  ██████╗ ███████╗"
echo "  ██╔══██╗██╔══██╗██║██╔══██╗██╔════╝ ██╔════╝"
echo "  ██████╔╝██████╔╝██║██║  ██║██║  ███╗█████╗  "
echo "  ██╔══██╗██╔══██╗██║██║  ██║██║   ██║██╔══╝  "
echo "  ██████╔╝██║  ██║██║██████╔╝╚██████╔╝███████╗"
echo "  ╚═════╝ ╚═╝  ╚═╝╚═╝╚═════╝  ╚═════╝ ╚══════╝"
echo "  GGS Controller → Home Assistant Bridge"
echo ""
echo "[install] Starte Installation..."

# 1. System packages
echo "[install] Installing system packages..."
apt-get update -qq
apt-get install -y -qq \
  python3 python3-pip python3-venv \
  mosquitto mosquitto-clients \
  iptables netfilter-persistent \
  network-manager \
  openssl \
  rsync

# 2. Project directory
echo "[install] Creating $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
rsync -a --exclude='.git' --exclude='.venv' \
  "$(dirname "$0")/../" "$INSTALL_DIR/"

# 3. Python venv
echo "[install] Setting up Python venv..."
python3 -m venv "$VENV"
"$VENV/bin/pip" install -q --upgrade pip
"$VENV/bin/pip" install -q -r "$INSTALL_DIR/requirements.txt"

# 4. Mosquitto config
echo "[install] Configuring Mosquitto..."
cp "$INSTALL_DIR/config/mosquitto.conf" /etc/mosquitto/conf.d/spiderfarmer.conf

systemctl enable mosquitto
systemctl restart mosquitto
echo "[install] Mosquitto configured and running"

# 5. TLS certificates (bundled in repo — real SF MQTT certs for controller compatibility)
CERT_DIR="$INSTALL_DIR/certs"
if [[ -f "$CERT_DIR/server.crt" && -f "$CERT_DIR/server.key" && -f "$CERT_DIR/ca.crt" ]]; then
  echo "[install] Certificates present — skipping"
else
  echo "[install] ERROR: certs/ missing from installation directory!"
  exit 1
fi

# 6. systemd services
echo "[install] Installing systemd services..."
sed "s|/opt/spiderfarmer-bridge|$INSTALL_DIR|g" \
  "$INSTALL_DIR/systemd/sf-proxy.service" \
  > /etc/systemd/system/sf-proxy.service
sed "s|/opt/spiderfarmer-bridge|$INSTALL_DIR|g" \
  "$INSTALL_DIR/systemd/sf-discovery.service" \
  > /etc/systemd/system/sf-discovery.service
systemctl daemon-reload
systemctl enable sf-proxy sf-discovery
echo "[install] Services installed"

# 7. Hotspot
echo "[install] Configuring hotspot..."
SF_SSID="$("$VENV/bin/python3" -c "import yaml; c=yaml.safe_load(open('$INSTALL_DIR/config/config.yaml')); print(c['hotspot']['ssid'])")"
SF_PASSWORD="$("$VENV/bin/python3" -c "import yaml; c=yaml.safe_load(open('$INSTALL_DIR/config/config.yaml')); print(c['hotspot']['password'])")"
SF_IP="$("$VENV/bin/python3" -c "import yaml; c=yaml.safe_load(open('$INSTALL_DIR/config/config.yaml')); print(c['hotspot']['ip'])")"
SF_CHANNEL="$("$VENV/bin/python3" -c "import yaml; c=yaml.safe_load(open('$INSTALL_DIR/config/config.yaml')); print(c['hotspot']['channel'])")"
SF_IFACE="$("$VENV/bin/python3" -c "import yaml; c=yaml.safe_load(open('$INSTALL_DIR/config/config.yaml')); print(c['hotspot']['interface'])")"
SF_SSID="$SF_SSID" SF_PASSWORD="$SF_PASSWORD" SF_IP="$SF_IP" SF_CHANNEL="$SF_CHANNEL" SF_IFACE="$SF_IFACE" \
  bash "$INSTALL_DIR/setup/hotspot.sh"

echo ""
echo "  ╔══════════════════════════════════════════════════╗"
echo "  ║          Installation abgeschlossen!             ║"
echo "  ╠══════════════════════════════════════════════════╣"
echo "  ║  SSID:     $SF_SSID"
echo "  ║  Pi-IP:    $SF_IP"
echo "  ╠══════════════════════════════════════════════════╣"
echo "  ║  Services starten:                               ║"
echo "  ║    systemctl start sf-proxy sf-discovery         ║"
echo "  ╠══════════════════════════════════════════════════╣"
echo "  ║  GGS Controller mit WLAN verbinden:              ║"
echo "  ║    SSID: $SF_SSID"
echo "  ║  Dann Logs beobachten:                           ║"
echo "  ║    journalctl -fu sf-proxy                       ║"
echo "  ║  MAC wird beim ersten Verbinden automatisch      ║"
echo "  ║  erkannt und in config.yaml gespeichert.         ║"
echo "  ╚══════════════════════════════════════════════════╝"
echo ""
