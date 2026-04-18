#!/usr/bin/env bash
# Bootstrap: Repo von GitHub laden und installieren
# Verwendung: bash <(curl -sSL https://raw.githubusercontent.com/iceboerg00/spiderfarmer-bridge/master/setup/bootstrap.sh)
set -euo pipefail

INSTALL_DIR="/opt/spiderfarmer-bridge"
REPO="https://github.com/iceboerg00/spiderfarmer-bridge.git"

echo ""
echo " _________      .__    .___          ___.         .__    .___              "
echo " /   _____/_____ |__| __| _/__________\_ |_________|__| __| _/ ____   ____  "
echo " \_____  \\\\____ \|  |/ __ |/ __ \_  __ \ __ \_  __ \  |/ __ | / ___\_/ __ \ "
echo " /        \  |_> >  / /_/ \  ___/|  | \/ \_\ \  | \/  / /_/ |/ /_/  >  ___/ "
echo "/_______  /   __/|__\____ |\___  >__|  |___  /__|  |__\____ |\___  / \___  >"
echo "        \/|__|           \/    \/          \/              \/_____/      \/  "
echo ""
echo "  Spider Farmer GGS → Home Assistant"
echo "  Bootstrap — lädt Repo und richtet alles ein"
echo ""

# Root prüfen
if [[ $EUID -ne 0 ]]; then
  echo "Fehler: Bitte als root ausführen: sudo bash <(curl ...)"
  exit 1
fi

# git installieren falls nötig
if ! command -v git &>/dev/null; then
  echo "[bootstrap] Installiere git..."
  apt-get update -qq
  apt-get install -y -qq git
fi

# Repo klonen oder aktualisieren
if [[ -d "$INSTALL_DIR/.git" ]]; then
  echo "[bootstrap] Repo bereits vorhanden — aktualisiere..."
  git -C "$INSTALL_DIR" pull --ff-only
else
  echo "[bootstrap] Klone Repository nach $INSTALL_DIR..."
  git clone "$REPO" "$INSTALL_DIR"
fi

echo "[bootstrap] Repository bereit."
echo ""

# Wizard ausführen (interaktive Konfiguration)
bash "$INSTALL_DIR/setup/wizard.sh" "$INSTALL_DIR"

# Installer ausführen
bash "$INSTALL_DIR/setup/install.sh"
