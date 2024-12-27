#!/bin/bash

# Konfiguration
REPO_URL="https://github.com/cheinisch/flight-map.git"  # Ersetze mit dem tatsächlichen Repository
INSTALL_DIR="/opt/flight-map"
CONFIG_FILE="$INSTALL_DIR/config.yaml"
SERVICE_NAME="flight-map"
USER="flightmapuser"
PORT=8080

# Voraussetzungen prüfen
echo "Prüfe Voraussetzungen..."
sudo apt update
sudo apt install -y git python3 python3-venv nginx

# Benutzer erstellen, falls nicht vorhanden
if ! id "$USER" &>/dev/null; then
    echo "Erstelle Benutzer $USER..."
    sudo useradd -m -s /bin/bash "$USER"
fi

# Projektverzeichnis erstellen
echo "Erstelle Installationsverzeichnis..."
sudo mkdir -p "$INSTALL_DIR"
sudo chown -R "$USER:$USER" "$INSTALL_DIR"

# Projekt herunterladen
echo "Lade Projekt von GitHub herunter..."
sudo -u "$USER" git clone "$REPO_URL" "$INSTALL_DIR" || {
    echo "Projekt bereits vorhanden, aktualisiere Repository..."
    cd "$INSTALL_DIR" && sudo -u "$USER" git pull
}

# Konfigurationsdatei prüfen
if [[ -f "$CONFIG_FILE" ]]; then
    echo "Bestehende Konfigurationsdatei gefunden. Werte werden übernommen."
    CONFIG_EXISTS=true
else
    echo "Keine bestehende Konfigurationsdatei gefunden. Neue Konfiguration wird erstellt."
    CONFIG_EXISTS=false
fi

if [[ "$CONFIG_EXISTS" == false ]]; then
    # Eigene Koordinaten abfragen
    echo "Geben Sie Ihre Koordinaten ein (im Format DD.DDD). Standard ist 0.0 für beide Werte."
    read -p "Breitengrad (Latitude, Standard: 0.0): " LAT
    LAT=${LAT:-0.0}
    read -p "Längengrad (Longitude, Standard: 0.0): " LON
    LON=${LON:-0.0}

    # Receiver abfragen
    RECEIVERS=()
    echo "Konfigurieren Sie die Receiver. Lassen Sie die IP-Adresse leer, um keine weiteren Receiver hinzuzufügen."
    while true; do
        read -p "Receiver IP-Adresse (leer lassen, um fertigzustellen): " RECEIVER_IP
        if [[ -z "$RECEIVER_IP" ]]; then
            break
        fi
        read -p "Receiver Bezeichnung: " RECEIVER_NAME
        RECEIVERS+=("- name: \"$RECEIVER_NAME\"")
        RECEIVERS+=("  ip: \"$RECEIVER_IP\"")
        RECEIVERS+=("  port: 30003")
    done

    # Konfigurationsdatei erstellen
    echo "Erstelle Konfigurationsdatei..."
    {
        echo "port: $PORT"
        echo "position:"
        echo "  lat: $LAT"
        echo "  lon: $LON"
        echo "sources:"
        for RECEIVER in "${RECEIVERS[@]}"; do
            echo "  $RECEIVER"
        done
    } | sudo tee "$CONFIG_FILE"
else
    echo "Bestehende Konfiguration wird verwendet:"
    cat "$CONFIG_FILE"
fi

# Virtuelle Umgebung erstellen und Abhängigkeiten installieren
echo "Richte virtuelle Umgebung ein..."
sudo -u "$USER" python3 -m venv "$INSTALL_DIR/venv"
sudo -u "$USER" "$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt"

# Systemd-Dienst erstellen
echo "Erstelle Systemd-Dienst..."
cat <<EOF | sudo tee "/etc/systemd/system/$SERVICE_NAME.service"
[Unit]
Description=Flight Map Web Interface Service
After=network.target

[Service]
User=$USER
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/python3 $INSTALL_DIR/main.py --config $CONFIG_FILE
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Dienst aktivieren und starten
echo "Aktiviere und starte den Dienst..."
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl start "$SERVICE_NAME"

# Nginx konfigurieren
echo "Konfiguriere Nginx..."
cat <<EOF | sudo tee "/etc/nginx/sites-available/$SERVICE_NAME"
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://localhost:$PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

sudo ln -sf "/etc/nginx/sites-available/$SERVICE_NAME" "/etc/nginx/sites-enabled/"
sudo systemctl restart nginx

# Fertig
echo "Installation abgeschlossen! Zugriff unter http://<server-ip>"
