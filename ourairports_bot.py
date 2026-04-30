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
COUNTRIES_CSV = "https://davidmegginson.github.io/ourairports-data/countries.csv"


def lade_csv(url, bezeichnung):
    print(f"  Lade {bezeichnung}...", end=" ", flush=True)
    with urllib.request.urlopen(url, timeout=30) as r:
        daten = list(csv.DictReader(io.TextIOWrapper(r, encoding='utf-8')))
    print(f"{len(daten)} Einträge")
    return daten


def durchlauf():
    airports  = lade_csv(AIRPORTS_CSV,  "Flughäfen")
    runways   = lade_csv(RUNWAYS_CSV,   "Runways")
    freqs     = lade_csv(FREQS_CSV,     "Frequenzen")
    navaids   = lade_csv(NAVAIDS_CSV,   "Nav-Aids")
    countries = lade_csv(COUNTRIES_CSV, "Länder")

    # Ländername + Kontinent
    country_map = {}
    for c in countries:
        code = c.get('code', '').strip()
        if code:
            country_map[code] = {
                'name':      c.get('name', ''),
                'continent': c.get('continent', '')
            }

    # Runways nach ICAO gruppieren (beide Enden)
    runway_map = {}
    for r in runways:
        ident = r.get('airport_ident', '')
        if not ident:
            continue
        entry = {}
        if r.get('le_ident'):   entry['le'] = r['le_ident']
        if r.get('he_ident'):   entry['he'] = r['he_ident']
        try: entry['length']   = int(r['length_ft'])
        except (ValueError, KeyError): pass
        try: entry['width']    = int(r['width_ft'])
        except (ValueError, KeyError): pass
        try: entry['le_hdg']   = round(float(r['le_heading_degT']), 1)
        except (ValueError, KeyError): pass
        try: entry['he_hdg']   = round(float(r['he_heading_degT']), 1)
        except (ValueError, KeyError): pass
        try: entry['le_elev']  = int(float(r['le_elevation_ft']))
        except (ValueError, KeyError): pass
        try: entry['he_elev']  = int(float(r['he_elevation_ft']))
        except (ValueError, KeyError): pass
        try: entry['le_thr']   = int(r['le_displaced_threshold_ft']) if r.get('le_displaced_threshold_ft') else 0
        except (ValueError, KeyError): pass
        try: entry['he_thr']   = int(r['he_displaced_threshold_ft']) if r.get('he_displaced_threshold_ft') else 0
        except (ValueError, KeyError): pass
        if r.get('surface'):    entry['surface']  = r['surface']
        if r.get('lighted') == '1': entry['lighted'] = True
        if r.get('closed')  == '1': entry['closed']  = True
        runway_map.setdefault(ident, []).append(entry)

    # Frequenzen nach ICAO gruppieren
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

    # Nav-Aids nach Flughafen gruppieren
    navaid_map = {}
    for n in navaids:
        airport = n.get('associated_airport', '').strip()
        if not airport:
            continue
        entry = {
            'ident': n.get('ident', ''),
            'name':  n.get('name', ''),
            'type':  n.get('type', ''),
            'freq':  n.get('frequency_khz', '')
        }
        if n.get('dme_channel'):            entry['dme_ch']  = n['dme_channel']
        if n.get('dme_frequency_khz'):      entry['dme_freq'] = n['dme_frequency_khz']
        if n.get('power'):                  entry['power']   = n['power']
        if n.get('usageType'):              entry['usage']   = n['usageType']
        try:
            mv = round(float(n['magnetic_variation_deg']), 1)
            if mv != 0: entry['mag_var'] = mv
        except (ValueError, KeyError):
            pass
        navaid_map.setdefault(airport, []).append(entry)

    katalog = {}
    for ap in airports:
        if ap.get('type') == 'closed':
            continue
        ident = ap.get('ident', '').strip()
        if not ident:
            continue

        iso = ap.get('iso_country', '')
        cinfo = country_map.get(iso, {})

        entry = {
            'name':       ap.get('name', ''),
            'type':       ap.get('type', ''),
            'country':    iso,
            'country_name': cinfo.get('name', ''),
            'continent':  cinfo.get('continent', ap.get('continent', '')),
            'region':     ap.get('iso_region', ''),
            'city':       ap.get('municipality', ''),
            'scheduled':  ap.get('scheduled_service', '') == 'yes'
        }

        try: entry['lat'] = round(float(ap['latitude_deg']), 4)
        except (ValueError, KeyError): pass
        try: entry['lon'] = round(float(ap['longitude_deg']), 4)
        except (ValueError, KeyError): pass
        try: entry['elev'] = int(float(ap['elevation_ft']))
        except (ValueError, KeyError): pass

        if ap.get('iata_code'):      entry['iata'] = ap['iata_code']
        if ap.get('gps_code') and ap['gps_code'] != ident: entry['gps'] = ap['gps_code']
        if ap.get('local_code'):     entry['local'] = ap['local_code']
        if ap.get('home_link'):      entry['web']   = ap['home_link']
        if ap.get('wikipedia_link'): entry['wiki']  = ap['wikipedia_link']

        rwy = runway_map.get(ident, [])
        if rwy: entry['runways'] = rwy

        frq = freq_map.get(ident, [])
        if frq: entry['freqs'] = frq

        nav = navaid_map.get(ident, [])
        if nav: entry['navaids'] = nav

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
