"""
Holt die heutigen Gebetszeiten für Kassel von vaktija.eu und haengt sie
an Gebetszeiten.csv an (bzw. aktualisiert die Zeile fuer heute, falls vorhanden).

Format der CSV-Zeile (Semikolon-getrennt), passend zu deinem bestehenden Script:
Datum;Fajr;Sunrise;Dhuhr;Asr;Maghrib;Isha;Jumuah

Datum-Format: YYYY-MM-DD  (z.B. 2026-08-07)
Zeiten-Format: HH:MM
"""

import re
import sys
from datetime import datetime
from pathlib import Path

import requests

URL = "https://vaktija.eu/de/kassel"
CSV_PATH = Path(__file__).parent / "Gebetszeiten.csv"

# User-Agent setzen, damit die Anfrage wie ein normaler Browser aussieht
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}

# Reihenfolge der Ueberschriften auf der deutschen Seite, in der Reihenfolge
# in der sie im HTML erscheinen: Fajr, Sunrise, Dhuhr, Asr, Maghrib, Isha
# Wir suchen jede Ueberschrift und die naechste HH:MM-Zeit danach.
SECTION_LABELS = [
    "Morgengebet",   # Fajr
    "Sonnenaufgang", # Sunrise
    "Mittagsgebet",  # Dhuhr
    "Nachmittagsgebet",  # Asr
    "Abendgebet",    # Maghrib
    "Nachtgebet",    # Isha
]

TIME_RE = re.compile(r"\b([01]\d|2[0-3]):([0-5]\d)\b")


def fetch_html() -> str:
    resp = requests.get(URL, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    return resp.text


def extract_times(html: str) -> dict:
    """
    Findet fuer jedes Label die naechstgelegene Uhrzeit danach im HTML-Text.
    Robust gegenueber HTML-Tags dazwischen, da wir Label-Position + Regex-Suche
    im nachfolgenden Text-Fenster nutzen.
    """
    results = {}
    for label in SECTION_LABELS:
        idx = html.find(label)
        if idx == -1:
            raise ValueError(f"Label nicht gefunden: {label}")
        window = html[idx: idx + 400]  # Zeit steht kurz nach der Ueberschrift
        match = TIME_RE.search(window)
        if not match:
            raise ValueError(f"Keine Uhrzeit nach Label gefunden: {label}")
        results[label] = match.group(0)
    return results


def build_csv_row(times: dict) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    fajr = times["Morgengebet"]
    sunrise = times["Sonnenaufgang"]
    dhuhr = times["Mittagsgebet"]
    asr = times["Nachmittagsgebet"]
    maghrib = times["Abendgebet"]
    isha = times["Nachtgebet"]
    # Jumuah (Freitagsgebet) wird von vaktija.eu nicht separat angezeigt;
    # als Platzhalter identisch zu Dhuhr, kannst du spaeter manuell anpassen
    # falls deine Gemeinde eine feste Jumuah-Zeit hat.
    jumuah = dhuhr
    return f"{today};{fajr};{sunrise};{dhuhr};{asr};{maghrib};{isha};{jumuah}"


def update_csv(new_row: str) -> None:
    today_key = new_row.split(";")[0]

    if not CSV_PATH.exists():
        header = "Datum;Fajr;Sunrise;Dhuhr;Asr;Maghrib;Isha;Jumuah\n"
        CSV_PATH.write_text(header + new_row + "\n", encoding="utf-8")
        print(f"Neue CSV erstellt mit Zeile fuer {today_key}")
        return

    lines = CSV_PATH.read_text(encoding="utf-8").splitlines()
    header = lines[0] if lines else "Datum;Fajr;Sunrise;Dhuhr;Asr;Maghrib;Isha;Jumuah"
    body = lines[1:] if lines else []

    # Bestehende Zeile fuer heute entfernen, falls vorhanden (Idempotenz)
    body = [ln for ln in body if not ln.strip().startswith(today_key)]
    body.append(new_row)

    # Nach Datum sortieren, damit die Datei chronologisch bleibt
    body.sort(key=lambda ln: ln.split(";")[0])

    CSV_PATH.write_text(header + "\n" + "\n".join(body) + "\n", encoding="utf-8")
    print(f"CSV aktualisiert, Zeile fuer {today_key} gesetzt.")


def main() -> int:
    try:
        html = fetch_html()
        times = extract_times(html)
        row = build_csv_row(times)
        update_csv(row)
        print("Erfolg:", row)
        return 0
    except Exception as exc:
        print(f"FEHLER: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
