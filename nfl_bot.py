from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
import xml.etree.ElementTree as ET
import time
import json
import re
import requests
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

AIP_URL = "https://aip.dfs.de/BasicAIP/"
NFL_FALLBACK_URL = "https://nfl.dfs.de/basic/scripts/stub/startApplication.php"
PAGE_SIZE = 400
OUTPUT_FILE = "nfl_katalog.json"


def warte(browser, timeout=20):
    WebDriverWait(browser, timeout).until(
        EC.presence_of_element_located((By.TAG_NAME, 'body'))
    )
    time.sleep(4)


def dhxr_entfernen(url):
    return re.sub(r'[?&]dhxr\d+=\d+', '', url).rstrip('?&')


def iframe_urls(browser):
    return [dhxr_entfernen(f.get_attribute('src') or '')
            for f in browser.find_elements(By.TAG_NAME, 'iframe') if f.get_attribute('src')]


def connector_url_bauen(base_url, pos_start, count):
    parsed = urlparse(base_url)
    params = parse_qs(parsed.query, keep_blank_values=True)
    for k in list(params.keys()):
        if k.startswith('dhxr'):
            del params[k]
    params['posStart'] = [str(pos_start)]
    params['count'] = [str(count)]
    new_query = urlencode({k: v[0] for k, v in params.items()})
    return urlunparse(parsed._replace(query=new_query))


def xml_parsen(xml_text):
    eintraege = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        print(f"  XML-Fehler: {e}")
        return eintraege
    for row in root.findall('row'):
        cells = [c.text or '' for c in row.findall('cell')]
        nummer = cells[2].strip() if len(cells) > 2 else ''
        teil   = cells[1].strip() if len(cells) > 1 else ''
        row_id = row.get('id', '')
        if nummer:
            eintraege.append({'id': row_id, 'nummer': nummer, 'teil': teil})
    return eintraege


def main():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")

    browser = webdriver.Chrome(options=options)

    try:
        print("1. BasicAIP...")
        browser.get(AIP_URL)
        warte(browser)

        nfl_url = next(
            (el.get_attribute('href') for el in browser.find_elements(By.TAG_NAME, 'a')
             if "Nachrichten" in el.text and "Luftfahrer" in el.text and el.get_attribute('href')),
            NFL_FALLBACK_URL
        )

        print("2. NFL-Startseite...")
        browser.get(nfl_url)
        warte(browser)
        pane_url = next((u for u in iframe_urls(browser) if 'showPaneSet' in u), None)

        print("3. Pane...")
        browser.get(pane_url)
        warte(browser)
        grid_url = next((u for u in iframe_urls(browser) if 'showGrid' in u), None)

        print("4. Grid laden...")
        browser.get(grid_url)
        time.sleep(6)

        ajax_urls = browser.execute_script("""
            return performance.getEntriesByType('resource')
                .map(e => e.name)
                .filter(u => u.includes('connGrid') || u.includes('connector'));
        """)

        connector_url = next((u for u in ajax_urls if 'connGrid' in u), None)
        if not connector_url:
            raise RuntimeError("Keine Connector-URL gefunden")

        total = browser.execute_script("return globalActiveDHTMLGridObject.getRowsNum();")
        print(f"   {total} Einträge gefunden")

        cookies = {c['name']: c['value'] for c in browser.get_cookies()}
        session = requests.Session()
        session.cookies.update(cookies)
        session.headers.update({'Referer': grid_url, 'User-Agent': 'Mozilla/5.0'})

        base_url = dhxr_entfernen(connector_url)
        alle = []

        for start in range(0, total, PAGE_SIZE):
            url = connector_url_bauen(base_url, start, PAGE_SIZE)
            r = session.get(url, timeout=30)
            zeilen = xml_parsen(r.text)
            alle.extend(zeilen)
            print(f"  {start:5d}–{min(start+PAGE_SIZE, total):5d}: {len(zeilen)} Einträge")

        # Deduplizieren
        seen = set()
        unique = []
        for e in alle:
            if e['nummer'] not in seen:
                seen.add(e['nummer'])
                unique.append(e)

        print(f"\n{len(unique)} eindeutige Einträge")

        export = {
            'aktualisiert': datetime.now().strftime('%d.%m.%Y'),
            'gesamt': len(unique),
            'eintraege': unique
        }

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(export, f, ensure_ascii=False, separators=(',', ':'))

        print(f"Gespeichert: {OUTPUT_FILE}")

    except Exception as e:
        import traceback
        print(f"Fehler: {e}")
        traceback.print_exc()
        raise

    finally:
        browser.quit()


if __name__ == '__main__':
    main()
