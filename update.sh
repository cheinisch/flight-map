#!/bin/bash

# Konfiguration
REPO_URL="https://github.com/cheinisch/flight-map.git"  # Repository-URL
INSTALL_DIR="/opt/flight-map"
SERVICE_NAME="flight-map"
BACKUP_DIR="/opt/flight-map-backups"
TIMESTAMP=$(date +'%Y%m%d_%H%M%S')

echo "Update des Flight-Map-Dienstes gestartet..."

# Backup von user-config erstellen
if [ -d "$INSTALL_DIR/user-config" ]; then
    echo "Erstelle Backup des user-config-Ordners..."
    mkdir -p "$BACKUP_DIR"
    tar -czf "$BACKUP_DIR/user-config_backup_$TIMESTAMP.tar.gz" -C "$INSTALL_DIR" user-config || { 
        echo "Fehler beim Erstellen des Backups."; exit 1; 
    }
    echo "Backup erstellt unter $BACKUP_DIR/user-config_backup_$TIMESTAMP.tar.gz"
else
    echo "Ordner user-config nicht gefunden, kein Backup erforderlich."
fi

# Aktuelles Verzeichnis sichern
cd "$INSTALL_DIR" || { echo "Installationsverzeichnis $INSTALL_DIR nicht gefunden."; exit 1; }

# Entferne alle Dateien außer update.sh und user-config
echo "Entferne alte Dateien außer update.sh und user-config..."
find . -mindepth 1 ! -name 'update.sh' ! -path './user-config*' -exec rm -rf {} +

# Repository neu klonen
echo "Klone das Repository neu..."
git clone "$REPO_URL" temp_repo || { echo "Fehler beim Klonen des Repositories."; exit 1; }
mv temp_repo/* .
mv temp_repo/.* . 2>/dev/null
rmdir temp_repo

# Sicherstellen, dass der Ordner user-config weiterhin existiert
if [ ! -d "user-config" ]; then
    echo "Erstelle den Ordner user-config..."
    mkdir user-config
fi

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
