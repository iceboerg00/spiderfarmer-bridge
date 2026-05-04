#!/usr/bin/env bash
# Bootstrap: pull the repo from GitHub and install it.
# Usage: bash <(curl -sSL https://raw.githubusercontent.com/iceboerg00/spiderfarmer-bridge/master/setup/bootstrap.sh)
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
echo "  Bootstrap — clones the repo and runs the installer"
echo ""

# Require root
if [[ $EUID -ne 0 ]]; then
  echo "Error: please run as root: sudo bash <(curl ...)"
  exit 1
fi

# Install git if missing
if ! command -v git &>/dev/null; then
  echo "[bootstrap] Installing git..."
  apt-get update -qq
  apt-get install -y -qq git
fi

# Clone or update the repo
if [[ -d "$INSTALL_DIR/.git" ]]; then
  echo "[bootstrap] Repo already present — updating..."
  git -C "$INSTALL_DIR" pull --ff-only
else
  echo "[bootstrap] Cloning repository to $INSTALL_DIR..."
  git clone "$REPO" "$INSTALL_DIR"
fi

echo "[bootstrap] Repository ready."
echo ""

# Run the interactive wizard
bash "$INSTALL_DIR/setup/wizard.sh" "$INSTALL_DIR"

# Run the installer
bash "$INSTALL_DIR/setup/install.sh"
