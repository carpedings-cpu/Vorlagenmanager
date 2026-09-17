#!/usr/bin/env python3
"""Erzeugt das Monteurhotel-Cockpit als eine HTML-Datei.

    python3 werkzeuge/cockpit.py                    # in den Datenordner
    python3 werkzeuge/cockpit.py ~/Desktop/kpc.html # woandershin
    python3 werkzeuge/cockpit.py --artifact <ziel>  # zum Veröffentlichen

Die Stammdaten werden in die Datei hineingeschrieben, nicht nachgeladen: Die
Seite soll ohne Server laufen, per Doppelklick und aus SharePoint heraus. Nach
jeder Änderung an Baustellen oder Monteuren neu erzeugen.

Was die Seite kann und was nicht: Sie stellt den Suchauftrag zusammen, führt
den Belegungsplan und die Buchungshistorie. Die Verfügbarkeit fragt sie nicht
ab, das kann kein Browser ohne Zugang zu den Hotelportalen. Dafür erzeugt sie
den Auftragstext, der an Claude geht, und als Notnagel einen Booking-Link.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import hotels  # noqa: E402
from kern import repowurzel  # noqa: E402

PLATZHALTER = re.compile(r"/\*\{\{(\w+)\}\}\*/(\[\]|\{\})?")


def _baustellen() -> list[dict]:
    ausgabe = []
    for b in hotels.lade_baustellen():
        koord = b.get("koordinaten") or {}
        if not koord.get("lat") or not koord.get("lon"):
            print(
                f"  Übersprungen: {b.get('kurzname', '?')} hat keine Koordinaten",
                file=sys.stderr,
            )
            continue
        ausgabe.append(
            {
                "kuerzel": b.get("kuerzel", ""),
                "kurzname": b.get("kurzname", ""),
                "projektnummer": b.get("projektnummer", ""),
                "strasse": b.get("strasse", ""),
                "plz": str(b.get("plz", "")),
                "ort": b.get("ort", ""),
                "koordinaten": {"lat": koord["lat"], "lon": koord["lon"]},
                "max_entfernung_km": b.get("max_entfernung_km"),
                "max_preis_pro_nacht": b.get("max_preis_pro_nacht"),
                "hinweis": b.get("hinweis", ""),
            }
        )
    return ausgabe


def _monteure() -> list[dict]:
    return [
        {
            "kuerzel": m.get("kuerzel", ""),
            "name": m.get("name", ""),
            "fahrzeug": m.get("fahrzeug", ""),
            # Wer im Büro sitzt, taucht nicht in der Besetzungsauswahl auf,
            # bleibt aber in der Stammdatenübersicht sichtbar.
            "buero": bool(m.get("buero", False)),
            "hinweis": m.get("hinweis", ""),
        }
        for m in hotels.lade_monteure()
    ]


def _ohne_rahmen(text: str) -> str:
    """Schält Titel, Stil und Seiteninhalt aus dem vollständigen Dokument.

    Beim Veröffentlichen setzt die Plattform doctype, html, head und body
    selbst. Bleiben die eigenen stehen, wird das Dokument verschachtelt.
    """
    titel = re.search(r"<title>.*?</title>", text, re.S)
    stil = re.search(r"<style>.*?</style>", text, re.S)
    koerper = re.search(r"<body[^>]*>(.*)</body>", text, re.S)
    if not (titel and stil and koerper):
        raise ValueError("Template hat nicht die erwartete Form.")
    return "\n".join([titel.group(0), stil.group(0), koerper.group(1).strip()])


def erzeuge(ziel: Path | None = None, artifact: bool = False) -> Path:
    vorlage = repowurzel() / "vorlagen" / "cockpit" / "template.html"
    if not vorlage.exists():
        raise FileNotFoundError(f"{vorlage} fehlt.")

    daten = {
        "BAUSTELLEN": _baustellen(),
        "MONTEURE": _monteure(),
        "BUCHUNGEN": hotels.lade_buchungen(),
        "KRITERIEN": hotels.lade_kriterien(),
        "STAND": date.today().strftime(hotels.DATUMSFORMAT),
    }

    def ersetze(treffer: re.Match) -> str:
        name = treffer.group(1)
        if name not in daten:
            return treffer.group(0)
        wert = daten[name]
        if isinstance(wert, str):
            return wert
        return json.dumps(wert, ensure_ascii=False)

    text = PLATZHALTER.sub(ersetze, vorlage.read_text(encoding="utf-8"))

    offen = PLATZHALTER.findall(text)
    if offen:
        raise ValueError(
            "Unbelegte Platzhalter im Template: "
            + ", ".join(name for name, _ in offen)
        )

    if artifact:
        text = _ohne_rahmen(text)

    ziel = Path(ziel) if ziel else hotels.hotelordner() / "cockpit.html"
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_text(text, encoding="utf-8")
    return ziel


def main() -> int:
    argumente = sys.argv[1:]
    artifact = "--artifact" in argumente
    if artifact:
        argumente.remove("--artifact")
    if len(argumente) > 1:
        print(__doc__)
        return 1
    try:
        ziel = erzeuge(argumente[0] if argumente else None, artifact=artifact)
    except (FileNotFoundError, LookupError, ValueError) as fehler:
        print(f"Fehler: {fehler}", file=sys.stderr)
        return 1

    groesse = ziel.stat().st_size / 1024
    print(f"Cockpit: {ziel} ({groesse:.0f} kB)")
    print(
        f"  {len(hotels.lade_baustellen())} Baustellen, "
        f"{len(hotels.lade_monteure())} Leute, "
        f"{len(hotels.lade_buchungen())} Buchungen"
    )
    print("\nPer Doppelklick öffnen. Nach Änderungen an den Stammdaten neu erzeugen.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
