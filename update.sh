#!/bin/bash

echo "Starte Update des Dienstes..."
REPO_URL="https://github.com/cheinisch/flight-map.git"
PORT=8080

# Projektverzeichnis aktualisieren
echo "Lade neueste Version von GitHub herunter..."
sudo -u $USER git -C $INSTALL_DIR pull || sudo -u $USER git clone $REPO_URL $INSTALL_DIR

# Sicherstellen, dass config.yaml nicht überschrieben wird
echo "Konfigurationsdatei wird beibehalten..."
CONFIG_FILE="$INSTALL_DIR/config.yaml"
if [ ! -f "$CONFIG_FILE" ]; then
    echo "WARNUNG: Keine bestehende Konfigurationsdatei gefunden!"
fi

# Virtuelle Umgebung aktualisieren
echo "Aktualisiere Abhängigkeiten..."
sudo -u $USER $INSTALL_DIR/venv/bin/pip install -r $INSTALL_DIR/requirements.txt

# Dienst neu starten
echo "Starte Dienst neu..."
sudo systemctl restart $SERVICE_NAME

echo "Update abgeschlossen."
