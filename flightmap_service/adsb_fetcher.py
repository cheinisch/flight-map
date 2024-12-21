import socket
import json

class ADSBDataFetcher:
    def __init__(self, config_file):
        with open(config_file, "r") as f:
            self.config = json.load(f)
        self.servers = self.config.get("fr24_servers", [])

    def fetch_from_server(self, host, port):
        try:
            with socket.create_connection((host, port), timeout=5) as s:
                data = s.recv(4096).decode("utf-8")
                return data.splitlines()
        except Exception as e:
            print(f"Error connecting to {host}:{port} - {e}")
            return []

    def get_combined_data(self, source):
        combined_data = []
        for server in self.servers:
            if source == "all" or server["name"] == source:
                data = self.fetch_from_server(server["host"], server["port"])
                for d in data:
                    parts = d.split(',')
                    if len(parts) > 4:  # Beispiel für Parsen
                        combined_data.append({
                            "id": parts[4],
                            "lat": float(parts[10]),
                            "lon": float(parts[11]),
                            "alt": parts[12],
                            "speed": parts[13],
                            "source": server["name"]
                        })
        return combined_data

    def get_sources(self):
        return [server["name"] for server in self.servers]
