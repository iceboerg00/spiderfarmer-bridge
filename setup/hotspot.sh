#!/usr/bin/env bash
set -euo pipefail

SSID="${SF_SSID:-SF-Bridge}"
PASSWORD="${SF_PASSWORD:-changeme123}"
IFACE="${SF_IFACE:-wlan0}"
IP="${SF_IP:-192.168.10.1}"
CHANNEL="${SF_CHANNEL:-6}"
CON_NAME="SF-Bridge-Hotspot"
DNS_CONF="/etc/NetworkManager/dnsmasq-shared.d/spiderfarmer.conf"
IPTABLES_RULES="/etc/iptables/rules.v4"

echo "[hotspot] Setting up hotspot: $SSID on $IFACE"

# DNS redirect: write config BEFORE hotspot starts so dnsmasq picks it up on first run
mkdir -p "$(dirname "$DNS_CONF")"
cat > "$DNS_CONF" <<EOF
address=/sf.mqtt.spider-farmer.com/$IP
EOF
echo "[hotspot] DNS redirect configured: sf.mqtt.spider-farmer.com -> $IP"

# Remove existing connection if present (idempotent)
nmcli con delete "$CON_NAME" 2>/dev/null || true

# Create hotspot (NM-managed dnsmasq will read DNS conf on connection start)
nmcli con add \
  type wifi \
  ifname "$IFACE" \
  con-name "$CON_NAME" \
  ssid "$SSID" \
  wifi.mode ap \
  wifi.band bg \
  wifi.channel "$CHANNEL" \
  wifi-sec.key-mgmt wpa-psk \
  wifi-sec.psk "$PASSWORD" \
  wifi-sec.proto rsn \
  wifi-sec.pairwise ccmp \
  wifi-sec.group ccmp \
  ipv4.method shared \
  ipv4.addresses "$IP/24" \
  ipv6.method disabled

nmcli con up "$CON_NAME"
echo "[hotspot] Hotspot up: $SSID / $IP"

# iptables: redirect port 8883 on wlan0 to local proxy
iptables -t nat -C PREROUTING -i "$IFACE" -p tcp --dport 8883 -j REDIRECT --to-ports 8883 2>/dev/null \
  || iptables -t nat -A PREROUTING -i "$IFACE" -p tcp --dport 8883 -j REDIRECT --to-ports 8883
echo "[hotspot] iptables REDIRECT rule set"

# Persist iptables rules
mkdir -p "$(dirname "$IPTABLES_RULES")"
iptables-save > "$IPTABLES_RULES"

# Enable IP forwarding
sysctl -w net.ipv4.ip_forward=1
if ! grep -q "net.ipv4.ip_forward=1" /etc/sysctl.d/90-sf-bridge.conf 2>/dev/null; then
  echo "net.ipv4.ip_forward=1" > /etc/sysctl.d/90-sf-bridge.conf
fi

echo "[hotspot] Done. Connect GGS Controller to Wi-Fi: $SSID"
echo "[hotspot] Test: ping $IP from the Pi to verify hotspot is up"
