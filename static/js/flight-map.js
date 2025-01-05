
let map;
let planeMarkers = {};
let squawkColors = {}; // Globale Variable für Squawk-Farben

function getIconForPlane(aircraft, isSelected = false) {
    // Standardfarben
    let baseColor = isSelected ? 'lightgreen' : (aircraft.seen > 20 ? 'coral' : 'green');

    // Prüfen, ob der Squawk-Code in den geladenen Farben vorhanden ist
    if (aircraft.squawk && squawkColors[aircraft.squawk]) {
        baseColor = squawkColors[aircraft.squawk];
    }

    const rotation = aircraft.track || 0;
    return L.divIcon({
        html: `
            <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 1792 1792" style="transform: rotate(${rotation}deg);">
                <g transform="matrix(0.70710678,-0.70710678,-0.70710678,-0.70710678,898.14773,1786.3393)">
                    <path fill="${baseColor}" d="m 1397,1324 q 0,-87 -149,-236 l -240,-240 143,-746 1,-6 q 0,-14 -9,-23 L 1079,9 q -9,-9 -23,-9 -21,0 -29,18 L 753,593 508,348 Q 576,110 576,96 576,82 567,73 L 503,9 Q 494,0 480,0 462,0 452,16 L 297,296 17,451 q -17,9 -17,28 0,14 9,23 l 64,65 q 9,9 23,9 14,0 252,-68 L 593,753 18,1027 q -18,8 -18,29 0,14 9,23 l 64,64 q 9,9 23,9 4,0 6,-1 l 746,-143 240,240 q 149,149 236,149 32,0 52.5,-20.5 20.5,-20.5 20.5,-52.5 z"/>
                </g>
            </svg>
        `,
        className: 'plane-icon',
        iconSize: [32, 32]
    });
}

async function updatePlanesOnMap() {
    try {
        const response = await fetch('/data');
        const data = await response.json();

        Object.keys(planeMarkers).forEach(icao => {
            if (!data.find(plane => plane.icao === icao)) {
                map.removeLayer(planeMarkers[icao]);
                delete planeMarkers[icao];
            }
        });

        data.forEach(aircraft => {
            if (!aircraft.lat || !aircraft.lon) return;

            const isSelected = localStorage.getItem('highlightedAircraft') === aircraft.icao;

            if (planeMarkers[aircraft.icao]) {
                planeMarkers[aircraft.icao]
                    .setLatLng([aircraft.lat, aircraft.lon])
                    .setIcon(getIconForPlane(aircraft, isSelected));
            } else {
                const marker = L.marker([aircraft.lat, aircraft.lon], { icon: getIconForPlane(aircraft, isSelected) }).addTo(map);
                marker.on('click', () => selectAircraft(aircraft));
                planeMarkers[aircraft.icao] = marker;
            }
        });
    } catch (error) {
        console.error('Error updating planes on the map:', error);
    }
}


async function updateTitle() {
    try {
        const response = await fetch('/aircraft_counts');
        const counts = await response.json();

        // Aktualisiere die Titelzeile
        const total = counts.total || 0;
        const withPosition = counts.with_position || 0;
        document.title = `Flightmap // Aircrafts ${total}/${withPosition}`;
    } catch (error) {
        console.error('Fehler beim Aktualisieren der Titelzeile:', error);
    }
}

async function fetchAircraftCounts() {
    try {
        const response = await fetch('/aircraft_counts');
        const counts = await response.json();

        // Gesamtanzahl und Anzahl mit Position aktualisieren
        document.getElementById('aircraft_total').textContent = counts.total || 0;
        document.getElementById('aircraft_position').textContent = counts.with_position || 0;
    } catch (error) {
        console.error('Fehler beim Abrufen der Flugzeuganzahl:', error);
    }
}

async function fetchAircraftData() {
    try {
        fetch('/data')
            .then(response => response.json())
            .then(data => {
                const table = document.getElementById('aircraft_table');
                const detailsContainer = document.querySelector('.aircraft-details');
                const highlightedIcao = localStorage.getItem('highlightedAircraft'); // Aus localStorage laden

                table.innerHTML = ''; // Tabelle leeren
                let aircraftSelected = false;

                data.forEach(aircraft => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${aircraft.icao || 'N/A'}</td>
                        <td class="hide_mobile">${aircraft.country || ''}</td>
                        <td>${aircraft.flight || ''}</td>
                        <td>${aircraft.altitude ? aircraft.altitude + ' ft' : 'N/A'}</td>
                        <td>${aircraft.speed ? aircraft.speed + ' kt' : 'N/A'}</td>
                        <td>${aircraft.squawk || ''}</td>
                        <td class="hide_mobile">${aircraft.receiver}</td>
                    `;

                    // Highlight wiederherstellen, falls ICAO übereinstimmt
                    if (aircraft.icao === highlightedIcao) {
                        row.classList.add('uk-background-primary');
                        showAircraftDetails(aircraft);
                        aircraftSelected = true;
                    }

                    // Event-Listener für Klick hinzufügen
                    row.addEventListener('click', () => {
                        // Prüfe, ob die Zeile bereits ausgewählt ist
                        if (row.classList.contains('uk-background-primary')) {
                            // Auswahl entfernen
                            row.classList.remove('uk-background-primary');
                            localStorage.removeItem('highlightedAircraft');
                            detailsContainer.classList.add('hidden');
                        } else {
                            // Entferne die Highlight-Klasse von allen Zeilen
                            document.querySelectorAll('#aircraft_table tr').forEach(r => r.classList.remove('uk-background-primary'));

                            // Füge Highlight-Klasse zur aktuellen Zeile hinzu
                            row.classList.add('uk-background-primary');

                            // Speichere ICAO im localStorage
                            localStorage.setItem('highlightedAircraft', aircraft.icao);

                            // Zeige Details in der Seitenleiste
                            showAircraftDetails(aircraft);
                            detailsContainer.classList.remove('hidden');
                        }
                    });

                    table.appendChild(row);
                });

                // Wenn kein Flugzeug ausgewählt ist, verstecke die Details
                if (!aircraftSelected) {
                    detailsContainer.classList.add('hidden');
                }
            })
            .catch(error => console.error('Fehler beim Abrufen der Flugzeugdaten:', error));
    } catch (error) {
        console.error('Fehler beim Abrufen der Flugzeugdaten:', error);
    }
}



function selectAircraft(aircraft) {
    localStorage.setItem('highlightedAircraft', aircraft.icao);
    showAircraftDetails(aircraft);
}

function showAircraftDetails(aircraft) {

    console.log('Aircraft details:', aircraft);

    document.getElementById('aircraft_details_airline').textContent = aircraft.airline || '';
    document.getElementById('aircraft_details_country').textContent = aircraft.country_details || 'N/A';
    document.getElementById('aircraft_details_tailnumber').textContent = aircraft.tail_number || 'N/A';
    document.getElementById('aircraft_details_tailnumber-head').textContent = ': ' + aircraft.tail_number || 'N/A';
    document.getElementById('aircraft_details_model').textContent = aircraft.model || 'N/A';
    document.getElementById('aircraft_details_squawk').textContent = aircraft.squawk || 'N/A';
    document.getElementById('aircraft_details_alt').textContent = aircraft.altitude ? `${aircraft.altitude} ft` : 'N/A';
    document.getElementById('aircraft_details_speed').textContent = aircraft.speed ? `${aircraft.speed} kt` : 'N/A';
    document.getElementById('aircraft_details_track').textContent = aircraft.track ? `${aircraft.track}°` : 'N/A';
    document.getElementById('aircraft_details_pos').textContent = `${aircraft.lat || 'N/A'}, ${aircraft.lon || 'N/A'}`;
    document.getElementById('aircraft_details_distance').textContent = aircraft.distance_km ? `${aircraft.distance_nm} nm (${aircraft.distance_km} km)` : 'N/A';
    document.getElementById('aircraft_details_last_seen').textContent = aircraft.seen ? `${aircraft.seen}s ago` : 'N/A';
}

async function initMap() {
    const config = await fetch('/config').then(res => res.json());
    map = L.map('map').setView([config.position.lat, config.position.lon], 10);
    //L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19 }).addTo(map);
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', { maxZoom: 19 }).addTo(map);
    await fetchSquawkColors(); // Farben laden
    updatePlanesOnMap();
}

async function fetchSquawkColors() {
    try {
        const response = await fetch('/squawk');
        if (!response.ok) {
            console.error('Failed to fetch squawk colors:', response.statusText);
            return;
        }

        const squawkData = await response.json();
        console.log('Loaded squawk colors:', squawkData); // Debugging

        // Konvertiere das Array in ein Objekt für schnellen Zugriff
        squawkColors = squawkData.reduce((acc, item) => {
            acc[item.squawk] = item.color;
            return acc;
        }, {});
        
        console.log('Converted squawk colors:', squawkColors); // Debugging
    } catch (error) {
        console.error('Error fetching squawk colors:', error);
    }
}

async function loadVersion() {
    try {
        const response = await fetch('/static/VERSION');
        if (response.ok) {
            const version = await response.text();
            document.getElementById('version-info').textContent = `Version: ${version.trim()}`;
        } else {
            console.error('Failed to load version information.');
        }
    } catch (error) {
        console.error('Error fetching version:', error);
    }
}

async function checkForUpdate() {
    try {
        const localVersion = await fetch('/static/VERSION').then(res => res.text());
        const remoteVersion = await fetch('https://raw.githubusercontent.com/cheinisch/flight-map/main/VERSION').then(res => res.text());
        
        if (localVersion.trim() !== remoteVersion.trim()) {
            document.getElementById('update-message').style.display = 'inline';
        }
    } catch (error) {
        console.error('Error checking for updates:', error);
    }
}

function runUpdateScript() {
    fetch('/run-update', { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            alert(data.message);
        })
        .catch(err => {
            console.error('Update failed:', err);
            alert('Update failed.');
        });
}

// Lade die Versionsnummer und prüfe auf Updates
loadVersion();
checkForUpdate();

initMap();
setInterval(fetchSquawkColors, 2000);
setInterval(updatePlanesOnMap, 2000);
setInterval(fetchAircraftCounts, 2000);
setInterval(fetchAircraftData, 2000);
setInterval(updateTitle, 2000);