#!/bin/bash

# Konfiguration
REPO_URL="https://github.com/cheinisch/flight-map.git"  # Repository-URL
INSTALL_DIR="/opt/flight-map"
SERVICE_NAME="flight-map"

echo "Update des Flight-Map-Dienstes gestartet..."

# Aktuelles Verzeichnis sichern
cd "$INSTALL_DIR" || { echo "Installationsverzeichnis $INSTALL_DIR nicht gefunden."; exit 1; }

# Entferne alle Dateien außer update.sh und config.yaml
echo "Entferne alte Dateien außer config.yaml und update.sh..."
find . -mindepth 1 ! -name 'update.sh' ! -name 'config.yaml' -exec rm -rf {} +

# Repository neu klonen
echo "Klone das Repository neu..."
git clone "$REPO_URL" temp_repo || { echo "Fehler beim Klonen des Repositories."; exit 1; }
mv temp_repo/* .
mv temp_repo/.* . 2>/dev/null
rmdir temp_repo

# Virtuelle Umgebung neu einrichten
echo "Richte virtuelle Umgebung ein..."
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt || { echo "Fehler beim Installieren der Abhängigkeiten."; exit 1; }
deactivate

# Systemd-Dienst neu starten
echo "Setze den Systemd-Dienst neu auf..."
sudo systemctl stop "$SERVICE_NAME"
sudo systemctl daemon-reload
sudo systemctl start "$SERVICE_NAME"

# Erfolgsmeldung
echo "Update abgeschlossen! Flight-Map-Dienst läuft unter http://<server-ip>"
