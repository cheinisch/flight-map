import yaml
import json
import time
from flask import Flask, jsonify, request, render_template
import socket
from flask_cors import CORS

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
CORS(app)  # CORS-Unterstützung aktivieren

# Daten zwischenspeichern
aircraft_data = {}

# Daten aus Quellen abrufen
def fetch_data():
    global aircraft_data
    while True:
        for source in SOURCES:
            ip, port, name = source['ip'], source['port'], source['name']
            try:
                print(f"Verbinde zu {ip}:{port} ({name})...")
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.connect((ip, port))
                    s.settimeout(1.0)
                    raw_data = s.recv(1024).decode('utf-8')
                    print(f"Empfangene Daten von {name}: {raw_data}")  # Debug-Ausgabe

                    for line in raw_data.split('\n'):
                        parts = line.split(',')
                        if len(parts) > 4:
                            icao = parts[0]
                            lat = float(parts[1])
                            lon = float(parts[2])
                            alt = float(parts[3])
                            speed = float(parts[4])

                            # Flugzeugdaten speichern
                            aircraft_data[icao] = {
                                'lat': lat, 'lon': lon, 'alt': alt, 'speed': speed, 'source': name
                            }

                            print(f"Gespeicherte Daten: {aircraft_data[icao]}")  # Debug-Ausgabe

            except Exception as e:
                print(f"Fehler beim Abrufen von {name} ({ip}:{port}): {e}")
        time.sleep(1)

# Endpunkte definieren
@app.route('/')
def index():
    return render_template('index.html', position=POSITION)

@app.route('/data', methods=['GET'])
def get_data():
    print('Aktuelle Daten:', aircraft_data)  # Debugging
    source = request.args.get('source', 'all')
    if source == 'all':
        return jsonify(list(aircraft_data.values()))
    else:
        filtered = [v for v in aircraft_data.values() if v['source'] == source]
        return jsonify(filtered)
    
@app.route('/test_connection', methods=['GET'])
def test_connection():
    try:
        ip = SOURCES[0]['ip']
        port = SOURCES[0]['port']
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((ip, port))
            s.settimeout(1.0)
            raw_data = s.recv(1024).decode('utf-8')
            return jsonify({'success': True, 'data': raw_data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/sources', methods=['GET'])
def get_sources():
    return jsonify([source['name'] for source in SOURCES])

@app.route('/config', methods=['GET'])
def get_config():
    try:
        print('Konfigurationsdaten:', config)  # Debug-Ausgabe
        return jsonify(config)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Anwendung starten
if __name__ == '__main__':
    from threading import Thread
    fetch_thread = Thread(target=fetch_data)
    fetch_thread.daemon = True
    fetch_thread.start()
    app.run(host='0.0.0.0', port=PORT)
