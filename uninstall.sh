#!/bin/bash
echo "Envious uninstaller"
echo "This script needs root permissions and will uninstall envious from /usr/bin/envious and uninstall the man page from /usr/share/man/man1/envious1.gz"
echo "Additionally it will remove the directory /var/lib/envious and any profiles within."
read -p "Is that acceptable? (y/N): " confirmation
if [[ "$confirmation" != "y" && "$confirmation" != "Y" ]]; then
    echo "Aborted."
    exit 0
fi
if [ "$(id -u)" -ne 0 ]; then
    echo "This script must be run as root."
    exit 66
fi
echo "Uninstalling..."
sudo rm /usr/bin/envious -f
sudo rm -rf /var/lib/envious -f
sudo rm /usr/share/man/man1/envious.1.gz -f
echo "Uninstall completed!"
