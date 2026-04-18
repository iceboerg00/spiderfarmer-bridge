#!/usr/bin/env bash
# Bootstrap: Repo von GitHub laden und installieren
# Verwendung: bash <(curl -sSL https://raw.githubusercontent.com/iceboerg00/spiderfarmer-bridge/master/setup/bootstrap.sh)
set -euo pipefail

INSTALL_DIR="/opt/spiderfarmer-bridge"
REPO="https://github.com/iceboerg00/spiderfarmer-bridge.git"

echo ""
echo "   _____ _____ _____ _____  _____ ____  "
echo "  / ____|  ___/ ____|  __ \|  ___/ __ \ "
echo " | (___ | |_ | |    | |__) | |_ | |  | |"
echo "  \___ \|  _|| |    |  _  /|  _|| |  | |"
echo "  ____) | |  | |____| | \ \| |  | |__| |"
echo " |_____/|_|   \_____|_|  \_\_|   \____/ "
echo ""
echo "  Spider Farmer GGS → Home Assistant Bridge"
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
