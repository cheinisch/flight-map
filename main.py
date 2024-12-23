import yaml
import json
import time
from flask import Flask, jsonify, request, render_template
import socket

# Konfiguration laden
def load_config(config_path):
    with open(config_path, 'r') as file:
        return yaml.safe_load(file)

config = load_config('config.yaml')
PORT = config['port']
POSITION = config['position']
SOURCES = config['sources']

# Flask-App erstellen
app = Flask(__name__)

# Daten zwischenspeichern
aircraft_data = {}

# Daten aus Quellen abrufen
def fetch_data():
    global aircraft_data
    while True:
        for source in SOURCES:
            ip, port, name = source['ip'], source['port'], source['name']
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.connect((ip, port))
                    s.settimeout(1.0)
                    raw_data = s.recv(1024).decode('utf-8')
                    for line in raw_data.split('\n'):
                        parts = line.split(',')
                        if len(parts) > 4:
                            icao = parts[0]
                            lat = float(parts[1])
                            lon = float(parts[2])
                            alt = float(parts[3])
                            speed = float(parts[4])
                            aircraft_data[icao] = {
                                'lat': lat, 'lon': lon, 'alt': alt, 'speed': speed, 'source': name
                            }
            except Exception as e:
                print(f"Fehler beim Abrufen von {name}: {e}")
        time.sleep(1)

# Endpunkte definieren
@app.route('/')
def index():
    return render_template('index.html', position=POSITION)

@app.route('/data', methods=['GET'])
def get_data():
    source = request.args.get('source', 'all')
    if source == 'all':
        return jsonify(list(aircraft_data.values()))
    else:
        filtered = [v for v in aircraft_data.values() if v['source'] == source]
        return jsonify(filtered)

@app.route('/sources', methods=['GET'])
def get_sources():
    return jsonify([source['name'] for source in SOURCES])

@app.route('/config', methods=['GET'])
def get_config():
    return jsonify(config_data)

# Anwendung starten
if __name__ == '__main__':
    from threading import Thread
    fetch_thread = Thread(target=fetch_data)
    fetch_thread.daemon = True
    fetch_thread.start()
    app.run(host='0.0.0.0', port=PORT)
