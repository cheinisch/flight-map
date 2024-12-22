#!/bin/bash

SERVICE_NAME="flight-map"
INSTALL_DIR="/opt/flight-map"
USER="flightmapuser"

# Dienst stoppen und deaktivieren
echo "Stoppe und deaktiviere den Dienst..."
sudo systemctl stop $SERVICE_NAME
sudo systemctl disable $SERVICE_NAME

# Systemd-Dienstdatei löschen
echo "Lösche Systemd-Dienstdatei..."
sudo rm /etc/systemd/system/$SERVICE_NAME.service
sudo systemctl daemon-reload
sudo systemctl reset-failed

# Nginx-Konfiguration entfernen
echo "Lösche Nginx-Konfiguration..."
sudo rm /etc/nginx/sites-available/$SERVICE_NAME
sudo rm /etc/nginx/sites-enabled/$SERVICE_NAME
sudo systemctl reload nginx

# Benutzer entfernen
echo "Lösche Benutzer und Heimatverzeichnis..."
sudo userdel -r $USER

# Installationsverzeichnis löschen
echo "Lösche Installationsverzeichnis..."
sudo rm -rf $INSTALL_DIR

# Fertig
echo "Deinstallation abgeschlossen."
