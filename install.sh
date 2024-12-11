#!/bin/bash
source /home/blyss/scripts/util.sh
watermark "Envious installer v0.1"
checkroot
sudo rm /usr/bin/envious
sudo cp envious.py /usr/bin/envious
sudo chmod +x /usr/bin/envious
sudo mkdir -p /usr/share/envious
techo "${GREEN}Installed!"
