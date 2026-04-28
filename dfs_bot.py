from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import json

BASIS_URL = "https://aip.dfs.de/BasicVFR/"

IGNORIEREN = {
    'AIP', 'Impressum', 'Disclamer', 'Datenschutz',
    'AD Flugplätze', 'AD 0 Inhalt', 'AD 1 Allgemeines',
    'AD 2 Liste der Flugplätze'
}


def warte(browser):
    WebDriverWait(browser, 10).until(
        EC.presence_of_element_located((By.TAG_NAME, 'a'))
    )
    time.sleep(1.5)


def alle_links(browser):
    return [(l.text.strip(), l.get_attribute('href'))
            for l in browser.find_elements(By.TAG_NAME, 'a')]


def ist_karte(text, href, fh_url):
    if not text or not href:
        return False
    if "aip.dfs.de" not in href:
        return False
    if href == fh_url:
        return False
    if any(x in href for x in ['#popupSearch', '#popupPermalink', 'javascript:']):
        return False
    if text in IGNORIEREN:
        return False
    if '»' in text:
        return False
    if len(text) < 3:
        return False
    return True


def main():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    browser = webdriver.Chrome(options=options)
    katalog = {}

    try:
        browser.get(BASIS_URL)
        warte(browser)

        # AD Flugplätze klicken
        for text, href in alle_links(browser):
            if "AD Flugplätze" in text:
                browser.execute_script(
                    "arguments[0].click();",
                    browser.find_element(By.LINK_TEXT, text)
                )
                break
        time.sleep(2)

        # Alphabet-Ordner URLs sammeln
        alphabet_urls = {}
        for text, href in alle_links(browser):
            t = text.replace('»', '').strip()
            if href and t in ['A','B','C-D','E-F','G-H','I-J','K-L','M','N','O-P','Q-R','S','T-U','V-Z']:
                alphabet_urls[t] = href

        print(f"{len(alphabet_urls)} Ordner: {list(alphabet_urls.keys())}")

        for ordner, ordner_url in alphabet_urls.items():
            print(f"\n=== {ordner} ===")
            browser.get(ordner_url)
            warte(browser)

            flughafen_urls = {}
            for text, href in alle_links(browser):
                if href and "ED" in text and "»" in text and len(text) > 6:
                    name = text.replace('»', '').strip()
                    flughafen_urls[name] = href

            print(f"  {len(flughafen_urls)} Flughäfen")

            for fh_name, fh_url in flughafen_urls.items():
                print(f"  {fh_name} ...", end=" ", flush=True)
                browser.get(fh_url)
                warte(browser)

                karten = {}
                for text, href in alle_links(browser):
                    if ist_karte(text, href, fh_url):
                        karten[text] = href

                print(f"({len(karten)} Karten)")
                katalog[fh_name] = {
                    "_url": fh_url,
                    "karten": karten
                }

        with open("dfs_katalog_export.json", "w", encoding="utf-8") as f:
            json.dump(katalog, f, indent=4, ensure_ascii=False)

        print(f"\nFertig! {len(katalog)} Flughäfen gespeichert.")

    except Exception as e:
        import traceback
        print(f"Fehler: {e}")
        traceback.print_exc()

    finally:
        browser.quit()


if __name__ == '__main__':
    main()
