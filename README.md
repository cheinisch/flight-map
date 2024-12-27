# Flight-Map

A real-time flight tracking application that uses data from ADS-B receivers and visualizes aircraft positions on a map.

## Features

- Real-time visualization of aircraft positions on an interactive map.
- Aircraft icons rotate to match their flight track.
- Dark mode support for the map.
- Highlights aircraft sending special squawk codes (e.g., 7X00 for emergencies).
- Detailed aircraft information including tail number, model, and position.
- Dynamically updated statistics for total aircraft and aircraft with positions.
- Supports multiple data sources (receivers).

## Prerequisites

- Python 3.8 or higher
- A web server capable of hosting Flask applications
- ADS-B receivers with `dump1090` or similar software providing aircraft data

## Installation

1. Clone the repository:
   ```bash
   wget -qO- https://raw.githubusercontent.com/cheinisch/flight-map/refs/heads/main/install.sh | sudo bash -s
   cd /opt/flightmap
   ```

2. Set up a virtual environment and install dependencies:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. Configure the application:
   - Edit the `config.yaml` file:
     - Set `port` to the desired port for the web server.
     - Define `position` with your receiver's latitude (`lat`) and longitude (`lon`).
     - Add ADS-B receiver sources under `sources` with their `ip` and `port`.

4. Start the application:
   ```bash
   python main.py
   ```
   Start the service:
   ```bash
   service flight-map start
   ```

5. Open your browser and navigate to `http://localhost:<port>` (replace `<port>` with the port defined in `config.yaml`).

## Configuration

The `config.yaml` file is used to configure the application:

```yaml
port: 8080
position:
  lat: 60.0000
  lon: 9.0000
sources:
  - name: "Receiver 1"
    ip: "192.168.1.10"
    port: 30003
  - name: "Receiver 2"
    ip: "192.168.1.11"
    port: 30003
```

## API Endpoints

- **`/`**: The main application interface.
- **`/data`**: JSON endpoint providing real-time aircraft data.
- **`/aircraft_counts`**: Returns total aircraft and those with positions.
- **`/config`**: Retrieves the current application configuration.
- **`/sources`**: Lists all configured data sources.

## Customization

- **Map Appearance**: Switch between light and dark map themes.
- **Aircraft Icons**: Customize aircraft icons, including rotation and color based on squawk codes.

## Contributing

1. Fork the repository.
2. Create your feature branch:
   ```bash
   git checkout -b feature/my-feature
   ```
3. Commit your changes:
   ```bash
   git commit -m "Add my feature"
   ```
4. Push to the branch:
   ```bash
   git push origin feature/my-feature
   ```
5. Open a pull request.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.

## Acknowledgments

- [OpenStreetMap](https://www.openstreetmap.org/) for the map tiles.
- [Leaflet.js](https://leafletjs.com/) for interactive map rendering.
- ADS-B data provided by `dump1090` or similar software.

## Contact

For questions or suggestions, please open an issue.
