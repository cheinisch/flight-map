import yaml
import json
import time
from flask import Flask, jsonify, request, render_template
import socket
import requests
from datetime import datetime
import math

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

# Hilfsfunktion: Flugzeugdaten basierend auf dem ICAO HEX Code abrufen
def fetch_aircraft_details(icao_hex):
    api_url = f"https://hexdb.io/api/v1/aircraft/{icao_hex}"
    retries = 3
    for attempt in range(retries):
        try:
            response = requests.get(api_url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if 'data' in data and len(data['data']) > 0:
                    aircraft_info = data['data'][0]
                    return {
                        "tail_number": aircraft_info.get("Registration", "Unknown"),
                        "model": aircraft_info.get("Type", "Unknown"),
                        "manufacturer": aircraft_info.get("Manufacturer", "Unknown"),
                        "country": aircraft_info.get("OperatorFlagCode", "Unknown"),
                        "owner": aircraft_info.get("RegisteredOwners", "Unknown")
                    }
            else:
                print(f"Fehler: HTTP {response.status_code}")
                return {}
        except requests.exceptions.RequestException as e:
            print(f"Verbindungsfehler für {icao_hex}: {e}")
            time.sleep(2)  # Warte vor dem nächsten Versuch
    return {
        "tail_number": "Unknown",
        "model": "Unknown",
        "manufacturer": "Unknown",
        "country": "Unknown",
        "owner": "Unknown"
    }

def calculate_distance(lat1, lon1, lat2, lon2):
    """Berechnet die Distanz zwischen zwei Punkten auf der Erde in nm und km."""
    R_km = 6371  # Erdradius in Kilometern
    R_nm = 3440  # Erdradius in Seemeilen

    # Konvertiere Grad in Radianten
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    # Haversine-Formel
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.asin(math.sqrt(a))

    # Entfernungen
    distance_km = R_km * c
    distance_nm = R_nm * c

    return distance_km, distance_nm

@app.route('/data', methods=['GET'])
def get_data():
    """
    Stellt die Flugzeugdaten bereit, einschließlich der aktuellsten Positionen
    und zusätzlicher Details wie Tailnummer, Modell und Land.
    """
    global aircraft_data
    receiver_lat = POSITION['lat']
    receiver_lon = POSITION['lon']

    # Überprüfen, ob die Konfiguration deaktiviert ist
    if receiver_lat == 0.0 and receiver_lon == 0.0:
        return jsonify({"message": "is in config disabled"})

    # Temporäre Struktur für die aktuellsten Daten
    latest_aircraft_data = {}

    # Abrufen der Daten von den Quellen und Aktualisierung von aircraft_data
    for source in SOURCES:
        receiver_ip = source['ip']
        dump1090_url = f"http://{receiver_ip}/dump1090/data/aircraft.json"
        try:
            response = requests.get(dump1090_url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                for ac in data.get('aircraft', []):
                    icao = ac.get('hex')
                    if icao:
                        # Falls bereits Daten für dieses ICAO vorhanden sind, nur die aktuellsten verwenden
                        existing = latest_aircraft_data.get(icao)
                        if not existing or ac.get('seen', float('inf')) < existing['seen']:
                            lat = ac.get('lat')
                            lon = ac.get('lon')

                            # Berechne Entfernung, falls Positionsdaten verfügbar sind
                            distance_km, distance_nm = (None, None)
                            if lat is not None and lon is not None:
                                distance_km, distance_nm = calculate_distance(receiver_lat, receiver_lon, lat, lon)

                            # Zusätzliche Details abrufen
                            aircraft_details = fetch_aircraft_details(icao)

                            # Track hinzufügen
                            track = ac.get('track')

                            latest_aircraft_data[icao] = {
                                'icao': icao,
                                'lat': lat,
                                'lon': lon,
                                'altitude': ac.get('altitude'),
                                'speed': ac.get('speed'),
                                'seen': ac.get('seen'),
                                'flight': ac.get('flight'),
                                'squawk': ac.get('squawk'),
                                'distance_km': round(distance_km, 2) if distance_km else None,
                                'distance_nm': round(distance_nm, 2) if distance_nm else None,
                                'receiver': source['name'],
                                'receiver_url': dump1090_url,
                                'track': track,
                                'tail_number': aircraft_details["tail_number"],
                                'model': aircraft_details["model"],
                                'manufacturer': aircraft_details["manufacturer"],
                                'country': aircraft_details["country"],
                                'owner': aircraft_details["owner"]
                            }
        except Exception as e:
            print(f"Fehler beim Abrufen der Daten von {receiver_ip}: {e}")

    # Filtere Flugzeuge, die älter als 120 Sekunden sind
    filtered_data = [
        ac for ac in latest_aircraft_data.values()
        if ac.get('seen') is not None and ac['seen'] <= 120
    ]

    print(f"Gefilterte Flugzeugdaten: {json.dumps(filtered_data, indent=2)}")
    return jsonify(filtered_data)


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

                # Filtere Flugzeuge, die in den letzten 120 Sekunden gesehen wurden
                recent_aircraft = [
                    ac for ac in aircraft
                    if 'seen' in ac and ac['seen'] <= 120
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