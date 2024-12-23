import yaml
import json
import time
from flask import Flask, jsonify, request, render_template
import socket
import logging

# Flask-Logger für weniger Lärm konfigurieren
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

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

def generate_dummy_data():
    # Dummy-Daten für Fallback
    return {
        'DUMMY1': {'lat': 50.1109, 'lon': 8.6821, 'alt': 10000, 'speed': 450, 'source': 'Dummy'},
        'DUMMY2': {'lat': 48.8566, 'lon': 2.3522, 'alt': 12000, 'speed': 500, 'source': 'Dummy'}
    }

# Daten aus Quellen abrufen
def fetch_data():
    global aircraft_data
    while True:
        try:
            for source in SOURCES:
                ip, port, name = source['ip'], source['port'], source['name']
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.connect((ip, port))
                        s.settimeout(10.0)
                        raw_data = s.recv(8192).decode('utf-8')
                        print(f"Empfangene Rohdaten von {name}: {raw_data[:100]}")  # Zeige die ersten 100 Zeichen

                        # Parsing der empfangenen Daten
                        for line in raw_data.split('\\n'):
                            parts = line.split(',')
                            if len(parts) > 10 and parts[0] == 'MSG' and parts[1] in ('3', '5'):
                                icao = parts[4]  # ICAO-Adresse
                                lat = float(parts[6]) if parts[6] else 50.1109  # Dummy Latitude
                                lon = float(parts[7]) if parts[7] else 8.6821  # Dummy Longitude
                                alt = float(parts[11]) if parts[11] else 0  # Höhe

                                # Speichern der Daten
                                aircraft_data[icao] = {
                                    'lat': lat,
                                    'lon': lon,
                                    'alt': alt,
                                    'speed': 0,
                                    'source': name
                                }
                                print(f"Gespeicherte Daten: {aircraft_data[icao]}")
                except Exception as e:
                    print(f"Fehler beim Abrufen von {name}: {e}")
            time.sleep(1)
        except Exception as e:
            print(f"Allgemeiner Fehler: {e}")

# Testverbindung zu einer Quelle
@app.route('/test_connection', methods=['GET'])
def test_connection():
    test_results = []
    for source in SOURCES:
        ip, port, name = source['ip'], source['port'], source['name']
        try:
            print(f"Teste Verbindung zu {name} ({ip}:{port})...")
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((ip, port))
                s.settimeout(10.0)
                raw_data = s.recv(8192).decode('utf-8')
                print(f"Empfangene Daten von {name}: {raw_data[:100]}...")  # Zeige nur die ersten 100 Zeichen
                test_results.append({
                    'source': name,
                    'status': 'success',
                    'sample_data': raw_data.split('\n')[:5]  # Zeige bis zu 5 Zeilen
                })
        except Exception as e:
            print(f"Fehler bei {name} ({ip}:{port}): {e}")
            test_results.append({
                'source': name,
                'status': 'error',
                'error': str(e)
            })
    return jsonify(test_results)

# Endpunkte definieren
@app.route('/')
def index():
    return render_template('index.html', position=POSITION)

@app.route('/data', methods=['GET'])
def get_data():
    print(f"Aktuelle Flugzeugdaten: {aircraft_data}")  # Debug-Ausgabe
    return jsonify(list(aircraft_data.values()))

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
