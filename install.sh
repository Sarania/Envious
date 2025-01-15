#!/bin/bash
echo "Envious installer"
echo "This script needs root permissions and will install envious.py to /usr/bin/envious, set it executable, and install the man page to /usr/share/man/man1/envious1.gz"
echo "Additionally it will create the directory /var/lib/envious for storing profiles if it does not already exist."
read -p "Is that acceptable? (y/N): " confirmation
if [[ "$confirmation" != "y" && "$confirmation" != "Y" ]]; then
    echo "Aborted."
    exit 0
fi
if [ "$(id -u)" -ne 0 ]; then
    echo "This script must be run as root."
    exit 66
fi
echo "Installing binary to /usr/bin/envious..."
sudo cp envious.py /usr/bin/envious
echo "Configuring permissions..."
sudo chmod +x /usr/bin/envious
echo "Creating profile directory(/var/lib/envious)..."
sudo mkdir -p /var/lib/envious
echo "Installing man page..."
sudo rm /usr/share/man/man1/envious.1.gz -f
sudo gzip -c envious.1 > /usr/share/man/man1/envious.1.gz
echo "Install completed!"
