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

# Remove existing hotspot connections (both legacy and current names)
nmcli con delete "$CON_NAME" 2>/dev/null || true
nmcli con delete PiHotspot   2>/dev/null || true
echo "[hotspot] Old connections removed (if existed)"

# Create hotspot (NM-managed dnsmasq will read DNS conf on connection start)
nmcli con add \
  type wifi \
  ifname "$IFACE" \
  con-name "$CON_NAME" \
  ssid "$SSID" \
  autoconnect yes \
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

# Stability tweaks: disable Wi-Fi powersave (was causing daily AP dropouts) and
# turn off Protected Management Frames (the GGS Controller does not negotiate
# PMF and silently drops association when it is required).
nmcli con modify "$CON_NAME" 802-11-wireless.powersave 2
nmcli con modify "$CON_NAME" 802-11-wireless-security.pmf 1

nmcli con up "$CON_NAME"
echo "[hotspot] Hotspot up: $SSID / $IP"

# Runtime powersave off in case the driver ignores the NM setting on first boot
iw dev "$IFACE" set power_save off 2>/dev/null || true

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
