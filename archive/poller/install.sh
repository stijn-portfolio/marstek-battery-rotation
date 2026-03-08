#!/bin/bash
# Marstek MQTT Poller - Installation Script
# =========================================
#
# Dit script installeert de Marstek MQTT Poller als systemd service.
#
# Gebruik:
#   sudo ./install.sh
#
# Na installatie:
#   - Edit /opt/marstek-poller/config.yaml met jouw instellingen
#   - sudo systemctl restart marstek-poller
#   - sudo journalctl -u marstek-poller -f  (bekijk logs)

set -e

INSTALL_DIR="/opt/marstek-poller"
SERVICE_NAME="marstek-poller"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "========================================"
echo "  Marstek MQTT Poller Installer"
echo "========================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "ERROR: Dit script moet als root draaien."
    echo "Gebruik: sudo ./install.sh"
    exit 1
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is niet geinstalleerd."
    echo "Installeer met: apt install python3 python3-pip"
    exit 1
fi

echo "[1/6] Creating installation directory..."
mkdir -p "$INSTALL_DIR"

echo "[2/6] Copying files..."
cp "$SCRIPT_DIR/marstek_poller.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/requirements.txt" "$INSTALL_DIR/"

# Copy config if it doesn't exist
if [ ! -f "$INSTALL_DIR/config.yaml" ]; then
    cp "$SCRIPT_DIR/config.yaml" "$INSTALL_DIR/"
    echo "       config.yaml gekopieerd (pas aan naar jouw setup!)"
else
    echo "       config.yaml bestaat al (niet overschreven)"
fi

echo "[3/6] Installing Python dependencies..."
pip3 install -r "$INSTALL_DIR/requirements.txt" --quiet

echo "[4/6] Installing systemd service..."
cp "$SCRIPT_DIR/marstek-poller.service" "/etc/systemd/system/"
systemctl daemon-reload

echo "[5/6] Enabling service..."
systemctl enable "$SERVICE_NAME"

echo "[6/6] Starting service..."
systemctl start "$SERVICE_NAME"

# Check status
sleep 2
if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo ""
    echo "========================================"
    echo "  INSTALLATIE GESLAAGD!"
    echo "========================================"
    echo ""
    echo "De Marstek MQTT Poller draait nu."
    echo ""
    echo "Volgende stappen:"
    echo "  1. Edit config:    sudo nano /opt/marstek-poller/config.yaml"
    echo "  2. Restart:        sudo systemctl restart marstek-poller"
    echo "  3. Bekijk logs:    sudo journalctl -u marstek-poller -f"
    echo "  4. Check status:   sudo systemctl status marstek-poller"
    echo ""
    echo "MQTT topics:"
    echo "  - marstek/marstek_fasea_d828/state"
    echo "  - marstek/marstek_faseb_9a7d/state"
    echo "  - marstek/marstek_fasec_deb8/state"
    echo ""
else
    echo ""
    echo "========================================"
    echo "  WAARSCHUWING: Service niet gestart"
    echo "========================================"
    echo ""
    echo "Check de logs voor meer info:"
    echo "  sudo journalctl -u marstek-poller -n 50"
    echo ""
fi
