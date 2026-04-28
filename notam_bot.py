import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime

DFS_VFR_URL = "https://www.dfs.de/homepage/de/medien/ifr-vfr-informationen/vfr-informationen/"

FALLBACK_URL = "https://www.dfs.de/homepage/de/medien/ifr-vfr-informationen/vfr-informationen/21-10-2022-notam-von-a-bis-z/2823-notam-heftchen-neu-2022-web-ds.pdf"

def suche_notam_pdf():
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(DFS_VFR_URL, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        for link in soup.find_all("a", href=True):
            href = link["href"]
            text = link.get_text(strip=True).lower()
            if "notam" in text and href.endswith(".pdf"):
                if href.startswith("http"):
                    return href
                else:
                    return "https://www.dfs.de" + href

        print("Kein neues PDF gefunden, verwende Fallback-URL.")
        return FALLBACK_URL

    except Exception as e:
        print(f"Fehler beim Abrufen: {e} — verwende Fallback-URL.")
        return FALLBACK_URL


def main():
    pdf_url = suche_notam_pdf()
    print(f"NOTAM PDF URL: {pdf_url}")

    daten = {
        "pdf_url": pdf_url,
        "aktualisiert": datetime.now().strftime("%d.%m.%Y")
    }

    with open("notam_info.json", "w", encoding="utf-8") as f:
        json.dump(daten, f, indent=4)

    print("notam_info.json gespeichert.")


if __name__ == "__main__":
    main()
