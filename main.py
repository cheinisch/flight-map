import yaml
import json
import time
from flask import Flask, jsonify, request, render_template
import requests
from datetime import datetime
import math
import logging

# Logging-Konfiguration
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(levelname)s] %(message)s')

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

# Hilfsfunktion: Flugzeugdetails basierend auf ICAO abrufen
def fetch_aircraft_details(icao_hex):
    api_url = f"https://hexdb.io/api/v1/aircraft/{icao_hex}"
    try:
        response = requests.get(api_url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return {
                "tail_number": data.get("Registration", "Unknown"),
                "model": data.get("Type", "Unknown"),
                "manufacturer": data.get("Manufacturer", "Unknown"),
                "country": data.get("OperatorFlagCode", "Unknown"),
                "owner": data.get("RegisteredOwners", "Unknown"),
            }
    except Exception as e:
        logging.error(f"Fehler beim Abrufen der Details für {icao_hex}: {e}")
    return {
        "tail_number": "Unknown",
        "model": "Unknown",
        "manufacturer": "Unknown",
        "country": "Unknown",
        "owner": "Unknown",
    }

# Hilfsfunktion: Entfernung berechnen
def calculate_distance(lat1, lon1, lat2, lon2):
    R_km = 6371  # Erdradius in km
    R_nm = 3440  # Erdradius in Seemeilen
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.asin(math.sqrt(a))
    distance_km = round(R_km * c, 2)
    distance_nm = round(R_nm * c, 2)
    return distance_km, distance_nm

# Hilfsfunktion History
def update_aircraft_history(aircraft):
    """
    Aktualisiert die Flugzeughistorie in der CSV-Datei.
    """
    updated_data = []
    icao_found = False
    with open(HISTORY_FILE, 'r') as file:
        reader = csv.DictReader(file)
        updated_data = list(reader)
    
    # Überprüfe, ob das Flugzeug bereits vorhanden ist
    for record in updated_data:
        if record['icao'] == aircraft['icao']:
            record.update({
                'tail_number': aircraft.get('tail_number', 'Unknown'),
                'manufacturer': aircraft.get('manufacturer', 'Unknown'),
                'model': aircraft.get('model', 'Unknown'),
                'last_seen': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
            icao_found = True
    
    # Falls nicht vorhanden, füge das Flugzeug hinzu
    if not icao_found:
        updated_data.append({
            'icao': aircraft['icao'],
            'tail_number': aircraft.get('tail_number', 'Unknown'),
            'manufacturer': aircraft.get('manufacturer', 'Unknown'),
            'model': aircraft.get('model', 'Unknown'),
            'last_seen': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })

    # Schreibe die aktualisierte Liste zurück in die Datei
    with open(HISTORY_FILE, 'w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=['icao', 'tail_number', 'manufacturer', 'model', 'last_seen'])
        writer.writeheader()
        writer.writerows(updated_data)

# Flugzeugdaten-Endpunkt
@app.route('/data', methods=['GET'])
def get_data():
    global aircraft_data
    receiver_lat, receiver_lon = POSITION['lat'], POSITION['lon']

    if receiver_lat == 0.0 and receiver_lon == 0.0:
        return jsonify({"message": "is in config disabled"})

    latest_aircraft_data = {}
    
    # Hier wird jedes Flugzeug aktualisiert
    for aircraft in latest_aircraft_data.values():
        update_aircraft_history(aircraft)

    # Daten von allen Quellen abrufen
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
                        existing = latest_aircraft_data.get(icao)
                        if not existing or ac.get('seen', float('inf')) < existing['seen']:
                            details = fetch_aircraft_details(icao)
                            distance_km, distance_nm = (
                                calculate_distance(receiver_lat, receiver_lon, ac.get('lat'), ac.get('lon'))
                                if ac.get('lat') and ac.get('lon') else (None, None)
                            )
                            latest_aircraft_data[icao] = {
                                'icao': icao,
                                'lat': ac.get('lat'),
                                'lon': ac.get('lon'),
                                'altitude': ac.get('altitude'),
                                'speed': ac.get('speed'),
                                'seen': ac.get('seen'),
                                'flight': ac.get('flight'),
                                'squawk': ac.get('squawk'),
                                'receiver': source['name'],
                                'receiver_url': dump1090_url,
                                'track': ac.get('track'),
                                'tail_number': details["tail_number"],
                                'model': details["model"],
                                'manufacturer': details["manufacturer"],
                                'country': details["country"],
                                'owner': details["owner"],
                                'distance_km': distance_km,
                                'distance_nm': distance_nm,
                            }
        except Exception as e:
            logging.error(f"Fehler beim Abrufen der Daten von {receiver_ip}: {e}")

    # Filtere veraltete Daten
    filtered_data = [
        ac for ac in latest_aircraft_data.values()
        if ac.get('seen') is not None and ac['seen'] <= 120
    ]

    logging.debug(f"Gefilterte Flugzeugdaten: {json.dumps(filtered_data, indent=2)}")
    return jsonify(filtered_data)

# Flugzeugzählungen
@app.route('/aircraft_counts', methods=['GET'])
def aircraft_counts():
    total, with_position = 0, 0
    for source in SOURCES:
        receiver_ip = source['ip']
        try:
            response = requests.get(f"http://{receiver_ip}/dump1090/data/aircraft.json", timeout=5)
            if response.status_code == 200:
                data = response.json()
                recent = [ac for ac in data.get('aircraft', []) if ac.get('seen') <= 120]
                total += len(recent)
                with_position += len([ac for ac in recent if ac.get('lat') and ac.get('lon')])
        except Exception as e:
            logging.error(f"Fehler beim Abrufen der Daten von {receiver_ip}: {e}")
    return jsonify({'total': total, 'with_position': with_position})

# Konfiguration
@app.route('/config', methods=['GET'])
def get_config():
    return jsonify(config)

@app.route('/history', methods=['GET'])
def get_history():
    """
    Gibt die Flugzeughistorie als JSON zurück.
    """
    try:
        with open(HISTORY_FILE, 'r') as file:
            reader = csv.DictReader(file)
            history_data = list(reader)

        # Konvertiere die CSV-Daten in ein JSON-kompatibles Format
        return jsonify(history_data)
    except Exception as e:
        return jsonify({'error': f"Error loading history: {e}"}), 500

@app.route('/')
def index():
    return render_template('index.html', position=POSITION)

# Anwendung starten
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)
