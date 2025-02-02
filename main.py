import yaml
import json
import time
from flask import Flask, jsonify, request, render_template, send_file
from apscheduler.schedulers.background import BackgroundScheduler
from subprocess import Popen, PIPE
import requests
from datetime import datetime
import math
import logging
import os
import csv

# Logging-Konfiguration
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(levelname)s] %(message)s')


# Verzeichnis für benutzerspezifische Konfigurationen
USER_CONFIG_DIR = os.path.join(os.getcwd(), 'user-config')
HISTORY_FILE = os.path.join(USER_CONFIG_DIR, 'aircraft_history.csv')

# Stelle sicher, dass der Ordner user-config existiert
os.makedirs(USER_CONFIG_DIR, exist_ok=True)

# Stelle sicher, dass die Datei existiert, falls sie nicht existiert
if not os.path.exists(HISTORY_FILE):
    with open(HISTORY_FILE, 'w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=['icao', 'tail_number', 'manufacturer', 'model', 'operator_flag', 'last_seen'])
        writer.writeheader()

# Konfiguration laden
def load_config(config_path='user-config/config.yaml'):
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found at {config_path}")
    with open(config_path, 'r') as file:
        return yaml.safe_load(file)

config = load_config()
PORT = config['port']
POSITION = config['position']
SOURCES = config['sources']

# Flask-App erstellen
app = Flask(__name__, static_folder='static')

# JSON-Datei für Country Codes
ICAO_CODES_FILE = os.path.join(os.getcwd(), 'config', 'icaocodes.json')

# Route für Country Codes
@app.route('/icaocode', methods=['GET'])
def get_icao_codes():
    """
    Gibt die icaocodes.json-Datei zurück.
    """
    if os.path.exists(ICAO_CODES_FILE):
        try:
            with open(ICAO_CODES_FILE, 'r') as file:
                icao_codes = json.load(file)
            return jsonify(icao_codes)
        except Exception as e:
            return jsonify({"error": f"Error reading icaocodes.json: {str(e)}"}), 500
    else:
        return jsonify({"error": "icaocodes.json not found"}), 404


# Hilfsfunktion: Ländername basierend auf dem Code abrufen
def get_icao_name(operator_flag_code):
    """
    Prüft, ob ein OperatorFlagCode in der icaocodes.json definiert ist,
    und gibt den entsprechenden Ländernamen und die Airline zurück.
    """

    try:
        if os.path.exists(ICAO_CODES_FILE):
            with open(ICAO_CODES_FILE, 'r') as file:
                icao_codes = json.load(file)
            # Durchlaufe die Liste und suche den passenden Code
            for entry in icao_codes:
                if entry.get('code') == operator_flag_code:
                    return {
                        "icao": entry.get('name', 'Unknown'),
                        "airline": entry.get('airline', 'Unknown'),
                        "country": entry.get('country', 'Unknown'),
                    }
    except Exception as e:
        logging.error(f"Error reading icaocodes.json: {e}")
    return {
        "icao": "Unknown",
        "airline": "Unknown"
    }

def get_country_from_tail_number(tail_number):
    if not tail_number:
        return "Unknown"
    with open('config/registration_prefixes.json', 'r') as file:
        prefixes = json.load(file)['prefixes']
    for entry in prefixes:
        if tail_number.startswith(entry['prefix']):
            return entry['country']
    return "Unknown"

# Hilfsfunktion: Flugzeugdetails basierend auf ICAO abrufen
def fetch_aircraft_details(icao_hex):
    api_url = f"https://hexdb.io/api/v1/aircraft/{icao_hex}"
    try:
        response = requests.get(api_url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            operator_flag_code = data.get("OperatorFlagCode", "Unknown")
            icao_info = get_icao_name(operator_flag_code)
            # Füge den Ländernamen und Airline-Namen nur in den Details hinzu
            icao_details = f"{operator_flag_code} ({icao_info['country']}, {icao_info['airline']})" if icao_info['airline'] != "Unknown" else operator_flag_code
            return {
                "tail_number": data.get("Registration", "Unknown"),
                "model": data.get("Type", "Unknown"),
                "manufacturer": data.get("Manufacturer", "Unknown"),
                "icao_operator_flag": operator_flag_code,  # Nur den Code für die Tabelle
                "icao_code_airline": icao_details,  # Land + Code für die Details
                "airline": icao_info["airline"],  # Airline
                "owner": data.get("RegisteredOwners", "Unknown"),
            }
    except Exception as e:
        logging.error(f"Fehler beim Abrufen der Details für {icao_hex}: {e}")
    return {
        "tail_number": "Unknown",
        "model": "Unknown",
        "manufacturer": "Unknown",
        "icao_operator_flag": "Unknown",
        "icao_code_airline": "Unknown",
        "airline": "Unknown",
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
    Aktualisiert die Flugzeughistorie in der CSV-Datei im Ordner 'user-config'.
    """
    updated_data = []
    icao_found = False

    # Lade vorhandene Einträge, wenn die Datei existiert
    if os.path.exists(HISTORY_FILE):
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
                'operator_flag': aircraft.get('icao_operator_flag', 'Unknown'),
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
            'operator_flag': aircraft.get('icao_operator_flag', 'Unknown'),
            'last_seen': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })

    # Schreibe die aktualisierte Liste zurück in die Datei
    with open(HISTORY_FILE, 'w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=['icao', 'tail_number', 'manufacturer', 'model', 'operator_flag', 'last_seen'])
        writer.writeheader()
        writer.writerows(updated_data)

# Automatisches mitloggen

def log_aircraft_history():
    try:
        response = requests.get('http://127.0.0.1:8080/data', timeout=10)
        if response.status_code == 200:
            aircraft_data = response.json()
            for aircraft in aircraft_data:
                update_aircraft_history(aircraft)
            logging.info("Aircraft history updated.")
        else:
            logging.error(f"Failed to fetch data: HTTP {response.status_code}")
    except Exception as e:
        logging.error(f"Error logging aircraft history: {e}")

# Scheduler starten
scheduler = BackgroundScheduler()
scheduler.add_job(log_aircraft_history, 'interval', seconds=60)
scheduler.start()

@app.route('/static/VERSION', methods=['GET'])
def get_version():
    version_file = os.path.join(os.getcwd(), 'VERSION')
    if os.path.exists(version_file):
        with open(version_file, 'r') as file:
            return file.read(), 200, {'Content-Type': 'text/plain'}
    else:
        return "Version file not found", 404

@app.route('/run-update', methods=['POST'])
def run_update():
    try:
        process = Popen(['bash', './update.sh'], cwd=os.getcwd(), stdout=PIPE, stderr=PIPE)
        stdout, stderr = process.communicate()
        if process.returncode == 0:
            return jsonify({'message': 'Update completed successfully!'})
        else:
            return jsonify({'message': f'Update failed: {stderr.decode("utf-8")}'})
    except Exception as e:
        return jsonify({'message': f'Error running update: {str(e)}'}), 500

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
                            reg_country = get_country_from_tail_number(details["tail_number"])
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
                                'registration_country': reg_country,
                                'model': details["model"],
                                'manufacturer': details["manufacturer"],
                                'icao_operator_flag': details["icao_operator_flag"],
                                'icao_code_airline': details["icao_code_airline"],
                                'airline': details["airline"],
                                'owner': details["owner"],
                                'distance_km': distance_km,
                                'distance_nm': distance_nm,
                            }
                            # Aktualisiere die Historie
                            update_aircraft_history(latest_aircraft_data[icao])
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
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r') as file:
                reader = csv.DictReader(file)
                history_data = list(reader)

            return jsonify(history_data)
        else:
            return jsonify({'error': "History file not found"}), 404
    except Exception as e:
        return jsonify({'error': f"Error loading history: {e}"}), 500
    
@app.route('/squawk', methods=['GET'])
def get_squawk():
    squawk_file = os.path.join(os.getcwd(), 'config', 'squawk.json')
    if os.path.exists(squawk_file):
        try:
            return send_file(squawk_file, mimetype='application/json')
        except Exception as e:
            return jsonify({"error": f"Error reading squawk.json: {str(e)}"}), 500
    else:
        return jsonify({"error": "squawk.json not found"}), 404

@app.route('/squawkuser', methods=['GET'])
def get_squawk_user():
    squawk_file = os.path.join(os.getcwd(), 'config-user', 'squawk.json')
    if os.path.exists(squawk_file):
        try:
            return send_file(squawk_file, mimetype='application/json')
        except Exception as e:
            return jsonify({"error": f"Error reading squawk.json: {str(e)}"}), 500
    else:
        return jsonify({"error": "squawk.json not found"}), 404

@app.route('/')
def index():
    return render_template('index.html', position=POSITION)

# Anwendung starten
if __name__ == '__main__':
    # Hintergrund-Logging aktivieren
    logging.info("Starting background aircraft logging...")
    scheduler = BackgroundScheduler()
    scheduler.add_job(log_aircraft_history, 'interval', seconds=60)
    scheduler.start()

    # Flask-App starten
    app.run(host='0.0.0.0', port=8080, debug=False)
