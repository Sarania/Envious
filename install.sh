#!/bin/bash
echo "Envious installer v0.1"
if [ "$(id -u)" -ne 0 ]; then
    echo "This script must be run as root."
    exit 66
fi
echo "Removing old binary..."
echo "Installing new binary..."
sudo cp envious.py /usr/bin/envious
echo "Configuring permissions..."
sudo chmod +x /usr/bin/envious
echo "Creating profile directory(/var/lib/envious)..."
sudo mkdir -p /var/lib/envious
echo "Installing man page..."
sudo rm /usr/share/man/man1/envious.1.gz -f
sudo gzip -c envious.1 > /usr/share/man/man1/envious.1.gz
echo "Install completed!"
