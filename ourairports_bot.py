import csv
import json
import io
import urllib.request
import subprocess
import time

AIRPORTS_CSV  = "https://davidmegginson.github.io/ourairports-data/airports.csv"
RUNWAYS_CSV   = "https://davidmegginson.github.io/ourairports-data/runways.csv"
FREQS_CSV     = "https://davidmegginson.github.io/ourairports-data/airport-frequencies.csv"
NAVAIDS_CSV   = "https://davidmegginson.github.io/ourairports-data/navaids.csv"


def lade_csv(url, bezeichnung):
    print(f"  Lade {bezeichnung}...", end=" ", flush=True)
    with urllib.request.urlopen(url, timeout=30) as r:
        daten = list(csv.DictReader(io.TextIOWrapper(r, encoding='utf-8')))
    print(f"{len(daten)} Einträge")
    return daten


def durchlauf():
    airports = lade_csv(AIRPORTS_CSV, "Flughäfen")
    runways  = lade_csv(RUNWAYS_CSV,  "Runways")
    freqs    = lade_csv(FREQS_CSV,    "Frequenzen")
    navaids  = lade_csv(NAVAIDS_CSV,  "Nav-Aids")

    # Runways nach ICAO-Ident gruppieren
    runway_map = {}
    for r in runways:
        ident = r.get('airport_ident', '')
        if not ident:
            continue
        entry = {}
        if r.get('surface'):
            entry['surface'] = r['surface']
        try:
            entry['length'] = int(r['length_ft'])
        except (ValueError, KeyError):
            pass
        try:
            entry['heading'] = round(float(r['le_heading_degT']), 1)
        except (ValueError, KeyError):
            pass
        if r.get('le_ident'):
            entry['id'] = r['le_ident']
        runway_map.setdefault(ident, []).append(entry)

    # Frequenzen nach ICAO-Ident gruppieren
    freq_map = {}
    for f in freqs:
        ident = f.get('airport_ident', '')
        if not ident:
            continue
        freq_map.setdefault(ident, []).append({
            'type': f.get('type', ''),
            'freq': f.get('frequency_mhz', ''),
            'desc': f.get('description', '')
        })

    # Nav-Aids nach zugehörigem Flughafen gruppieren
    navaid_map = {}
    for n in navaids:
        airport = n.get('associated_airport', '').strip()
        if not airport:
            continue
        freq_khz = n.get('frequency_khz', '')
        navaid_map.setdefault(airport, []).append({
            'ident': n.get('ident', ''),
            'name':  n.get('name', ''),
            'type':  n.get('type', ''),
            'freq':  freq_khz
        })

    katalog = {}
    for ap in airports:
        if ap.get('type') == 'closed':
            continue
        ident = ap.get('ident', '').strip()
        if not ident:
            continue

        entry = {
            'name':    ap.get('name', ''),
            'type':    ap.get('type', ''),
            'country': ap.get('iso_country', ''),
            'city':    ap.get('municipality', ''),
        }

        try:
            entry['lat'] = round(float(ap['latitude_deg']), 4)
        except (ValueError, KeyError):
            pass
        try:
            entry['lon'] = round(float(ap['longitude_deg']), 4)
        except (ValueError, KeyError):
            pass
        try:
            entry['elev'] = int(float(ap['elevation_ft']))
        except (ValueError, KeyError):
            pass

        if ap.get('iata_code'):
            entry['iata'] = ap['iata_code']
        if ap.get('home_link'):
            entry['web'] = ap['home_link']
        if ap.get('wikipedia_link'):
            entry['wiki'] = ap['wikipedia_link']

        rwy = runway_map.get(ident, [])
        if rwy:
            entry['runways'] = rwy

        frq = freq_map.get(ident, [])
        if frq:
            entry['freqs'] = frq

        nav = navaid_map.get(ident, [])
        if nav:
            entry['navaids'] = nav

        katalog[ident] = entry

    print(f"\n{len(katalog)} Flughäfen gespeichert (ohne geschlossene).")

    with open("ourairports_export.json", "w", encoding="utf-8") as f:
        json.dump(katalog, f, ensure_ascii=False, separators=(',', ':'))

    print("JSON geschrieben.")

    git = r"C:\Program Files\Git\cmd\git.exe"
    subprocess.run([git, "add", "ourairports_export.json"], check=True)
    result = subprocess.run([git, "commit", "-m", "Automatische Aktualisierung OurAirports"])
    if result.returncode == 0:
        subprocess.run([git, "push"], check=True)
        print("GitHub aktualisiert.")
    else:
        print("Keine Änderungen – kein Push nötig.")


def main():
    import sys
    if '--loop' in sys.argv:
        while True:
            print("Starte Durchlauf...")
            durchlauf()
            print("Nächster Durchlauf in 6 Stunden.\n")
            time.sleep(6 * 60 * 60)
    else:
        durchlauf()


if __name__ == '__main__':
    main()
