#!/bin/bash

# Konfiguration
REPO_URL="https://github.com/cheinisch/flight-map.git"
INSTALL_DIR="/opt/flight-map"
BACKUP_DIR="/opt/flight-map-backups"
SERVICE_NAME="flight-map"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/user-config_backup_${TIMESTAMP}.tar.gz"

echo "Update des Flight-Map-Dienstes gestartet..."

# Sicherstellen, dass Backup-Ordner existiert
if [ ! -d "$BACKUP_DIR" ]; then
    mkdir -p "$BACKUP_DIR"
    echo "Backup-Ordner erstellt: $BACKUP_DIR"
fi

# Backup der user-config
echo "Erstelle Backup der user-config unter $BACKUP_FILE..."
if tar -czf "$BACKUP_FILE" -C "$INSTALL_DIR" user-config; then
    echo "Backup erfolgreich: $BACKUP_FILE"
else
    echo "Fehler beim Erstellen des Backups!" >&2
    exit 1
fi

# Alte Dateien entfernen außer user-config und update.sh
echo "Entferne alte Dateien außer user-config und update.sh..."
find "$INSTALL_DIR" -mindepth 1 ! -name 'update.sh' ! -name 'user-config' -exec rm -rf {} +

# Repository aktualisieren
echo "Klone das Repository neu..."
git clone "$REPO_URL" temp_repo || { echo "Fehler beim Klonen des Repositories."; exit 1; }
mv temp_repo/* "$INSTALL_DIR"
mv temp_repo/.* "$INSTALL_DIR" 2>/dev/null || true
rmdir temp_repo

# Virtuelle Umgebung neu einrichten
echo "Richte virtuelle Umgebung ein..."
python3 -m venv "$INSTALL_DIR/venv"
source "$INSTALL_DIR/venv/bin/activate"
pip install -r "$INSTALL_DIR/requirements.txt" || { echo "Fehler beim Installieren der Abhängigkeiten."; deactivate; exit 1; }
deactivate

# Systemd-Dienst neu starten
echo "Setze den Systemd-Dienst neu auf..."
sudo systemctl stop "$SERVICE_NAME"
sudo systemctl daemon-reload
sudo systemctl start "$SERVICE_NAME"

echo "Update abgeschlossen!"
