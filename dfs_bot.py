from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import json

BASIS_URL = "https://aip.dfs.de/BasicVFR/"


def warte(browser):
    WebDriverWait(browser, 10).until(
        EC.presence_of_element_located((By.TAG_NAME, 'a'))
    )
    time.sleep(1)


def alle_links(browser):
    return [(l.text.strip(), l.get_attribute('href'))
            for l in browser.find_elements(By.TAG_NAME, 'a')]


def main():
    browser = webdriver.Chrome()
    katalog = {}

    try:
        # 1. Startseite laden und AD Flugplätze klicken
        browser.get(BASIS_URL)
        warte(browser)

        for text, href in alle_links(browser):
            if "AD Flugplätze" in text:
                browser.execute_script(
                    "arguments[0].click();",
                    browser.find_element(By.LINK_TEXT, text)
                )
                break
        time.sleep(2)

        # 2. Alle Alphabet-Ordner URLs auf einmal einsammeln (nicht klicken!)
        alphabet_urls = {}
        for text, href in alle_links(browser):
            t = text.replace('»', '').strip()
            if href and t in ['A','B','C-D','E-F','G-H','I-J','K-L','M','N','O-P','Q-R','S','T-U','V-Z']:
                alphabet_urls[t] = href

        print(f"{len(alphabet_urls)} Alphabet-Ordner gefunden: {list(alphabet_urls.keys())}")

        # 3. Jeden Ordner direkt aufrufen
        for ordner, ordner_url in alphabet_urls.items():
            print(f"\n=== Ordner: {ordner} ===")
            browser.get(ordner_url)
            warte(browser)

            # Flughafen-URLs einsammeln (nicht klicken!)
            flughafen_urls = {}
            for text, href in alle_links(browser):
                if href and "ED" in text and "»" in text and len(text) > 6:
                    name = text.replace('»', '').strip()
                    flughafen_urls[name] = href

            print(f"  {len(flughafen_urls)} Flughäfen gefunden.")

            # 4. Jeden Flughafen direkt aufrufen
            for fh_name, fh_url in flughafen_urls.items():
                print(f"  Scanne: {fh_name} ...", end=" ", flush=True)
                browser.get(fh_url)
                warte(browser)

                # Karten suchen
                karten = {}
                for text, href in alle_links(browser):
                    if text and href and ("Chart" in text or "Karte" in text or "Regelung" in text):
                        karten[text] = href

                print(f"({len(karten)} Karten)")
                katalog[fh_name] = {
                    "_url": fh_url,
                    "karten": karten
                }

        # 5. Speichern
        with open("dfs_katalog_export.json", "w", encoding="utf-8") as f:
            json.dump(katalog, f, indent=4, ensure_ascii=False)

        print(f"\nFertig! {len(katalog)} Flughäfen in 'dfs_katalog_export.json' gespeichert.")

    except Exception as e:
        import traceback
        print(f"Fehler: {e}")
        traceback.print_exc()

    finally:
        browser.quit()


if __name__ == '__main__':
    main()
