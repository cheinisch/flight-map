import yaml
import json
import time
from flask import Flask, jsonify, request, render_template
import socket
import requests
from datetime import datetime

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

@app.route('/data', methods=['GET'])
def get_data():
    global aircraft_data
    # Abrufen der Daten von den Quellen und Aktualisierung von aircraft_data
    for source in SOURCES:
        receiver_ip = source['ip']
        dump1090_url = f"http://{receiver_ip}/dump1090/data/aircraft.json"
        try:
            response = requests.get(dump1090_url)
            if response.status_code == 200:
                data = response.json()
                for ac in data.get('aircraft', []):
                    icao = ac.get('hex')
                    if icao:
                        aircraft_data[icao] = {
                            'icao': icao,
                            'lat': ac.get('lat'),
                            'lon': ac.get('lon'),
                            'alt': ac.get('alt_baro'),
                            'speed': ac.get('gs'),
                            'seen': ac.get('seen'),
                            'source': source['name']
                        }
        except Exception as e:
            print(f"Fehler beim Abrufen der Daten von {receiver_ip}: {e}")
    
    print(f"Aktuelle Flugzeugdaten: {json.dumps(aircraft_data, indent=2)}")
    return jsonify(list(aircraft_data.values()))

def fetch_aircraft_counts():
    """Zählt die Flugzeuge insgesamt und die mit Positionsdaten."""
    total_aircraft = 0
    aircraft_with_position = 0
    current_time = datetime.utcnow()

    for source in SOURCES:
        receiver_ip = source['ip']
        dump1090_url = f"http://{receiver_ip}/dump1090/data/aircraft.json"
        try:
            response = requests.get(dump1090_url)
            if response.status_code == 200:
                data = response.json()
                aircraft = data.get('aircraft', [])

                # Filtere Flugzeuge, die in den letzten 60 Sekunden gesehen wurden
                recent_aircraft = [
                    ac for ac in aircraft
                    if 'seen' in ac and ac['seen'] <= 60
                ]

                total_aircraft = len(recent_aircraft)
                aircraft_with_position = len([
                    ac for ac in recent_aircraft
                    if ac.get('lat') and ac.get('lon')
                ])
            else:
                print(f"Fehler beim Abrufen der Daten von {receiver_ip}: HTTP {response.status_code}")
        except Exception as e:
            print(f"Fehler beim Abrufen der Daten von {receiver_ip}: {e}")

    return {
        'total': total_aircraft,
        'with_position': aircraft_with_position
    }

# Endpunkte definieren
@app.route('/')
def index():
    return render_template('index.html', position=POSITION)

@app.route('/aircraft_counts', methods=['GET'])
def aircraft_counts():
    """Gibt die Gesamtzahl der Flugzeuge und die mit Positionsdaten zurück."""
    counts = fetch_aircraft_counts()
    return jsonify(counts)

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
    app.run(host='0.0.0.0', port=PORT)