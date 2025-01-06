#!/bin/bash

# Konfiguration
REPO_URL="https://github.com/cheinisch/flight-map.git"  # Ersetze mit dem tatsächlichen Repository
INSTALL_DIR="/opt/flight-map"
BACKUP_DIR="/opt/flight-map-backups"
SERVICE_NAME="flight-map"
USER="flightmapuser"
PORT=8080
USER_CONFIG_DIR="$INSTALL_DIR/user-config"
USER_CONFIG_BACKUP="$BACKUP_DIR/user-config_backup"

# Voraussetzungen prüfen
echo "Prüfe Voraussetzungen..."
sudo apt update
sudo apt install -y git python3 python3-venv nginx

# Benutzer erstellen, falls nicht vorhanden
if ! id "$USER" &>/dev/null; then
    echo "Erstelle Benutzer $USER..."
    sudo useradd -m -s /bin/bash "$USER"
fi

# Installations- und Backup-Verzeichnisse erstellen
echo "Erstelle Installations- und Backup-Verzeichnisse..."
sudo mkdir -p "$INSTALL_DIR"
sudo mkdir -p "$BACKUP_DIR"
sudo chown -R "$USER:$USER" "$INSTALL_DIR"
sudo chown -R "$USER:$USER" "$BACKUP_DIR"

# Sichern des user-config-Verzeichnisses
if [ -d "$USER_CONFIG_DIR" ]; then
    echo "Sichere user-config-Verzeichnis..."
    sudo cp -r "$USER_CONFIG_DIR" "$USER_CONFIG_BACKUP"
fi

# Projekt herunterladen
echo "Lade Projekt von GitHub herunter..."
sudo -u "$USER" git clone "$REPO_URL" "$INSTALL_DIR" || {
    echo "Projekt bereits vorhanden, aktualisiere Repository..."
    cd "$INSTALL_DIR" && sudo -u "$USER" git pull
}

# Wiederherstellung des user-config-Verzeichnisses
if [ -d "$USER_CONFIG_BACKUP" ]; then
    echo "Stelle user-config-Verzeichnis wieder her..."
    sudo cp -r "$USER_CONFIG_BACKUP" "$USER_CONFIG_DIR"
    sudo rm -rf "$USER_CONFIG_BACKUP"
fi

# Virtuelle Umgebung erstellen und Abhängigkeiten installieren
echo "Richte virtuelle Umgebung ein..."
sudo -u "$USER" python3 -m venv "$INSTALL_DIR/venv"
sudo -u "$USER" "$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt"

# Pfad zur Konfigurationsdatei
CONFIG_FILE="$INSTALL_DIR/user-config/config.yaml"

# Überprüfen, ob die Konfigurationsdatei bereits existiert
if [ -f "$CONFIG_FILE" ]; then
    echo "Konfigurationsdatei existiert bereits unter $CONFIG_FILE. Keine neue Datei wird erstellt."
else
    echo "Erstelle Konfigurationsdatei..."
    mkdir -p "$INSTALL_DIR/user-config"
    
    # Konfigurationsdatei erstellen
    cat <<EOF | sudo tee "$CONFIG_FILE"
port: $PORT
position:
  lat: 50.0357
  lon: 7.9491
sources:
  - name: "Pi"
    ip: 10.0.5.12
    port: 30003
  - name: "VM"
    ip: 10.0.5.10
    port: 30003
EOF
    echo "Konfigurationsdatei erstellt unter $CONFIG_FILE."
fi

# Systemd-Dienst erstellen
echo "Erstelle Systemd-Dienst..."
cat <<EOF | sudo tee "/etc/systemd/system/$SERVICE_NAME.service"
[Unit]
Description=Flight Map Web Interface Service
After=network.target
[Service]
User=$USER
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/python3 $INSTALL_DIR/main.py
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

# Server-IP abrufen
SERVER_IP=$(hostname -I | awk '{print $1}')

# Fertig
echo "Installation abgeschlossen! Zugriff unter http://$SERVER_IP:$PORT"
