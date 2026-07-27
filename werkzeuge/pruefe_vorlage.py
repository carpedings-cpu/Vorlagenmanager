#!/usr/bin/env python3
"""Prüft eine Vorlage auf Vollständigkeit.

    python3 werkzeuge/pruefe_vorlage.py vorlagen/bedenkenanmeldung
    python3 werkzeuge/pruefe_vorlage.py vorlagen/*/ --projekt projekte/2451_klinikum

Gemeldet werden Platzhalter ohne Felddefinition, Felder ohne Platzhalter und
unvollständige Felddefinitionen. Mit --projekt wird zusätzlich geprüft, ob die
Projektdatei alle Werte liefert, die über `quelle: projekt` gezogen werden.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from kern import (  # noqa: E402
    QUELLEN,
    blockschluessel,
    felder_nach_key,
    lade_vorlage,
    lade_yaml,
    platzhalter,
    projektordner,
    text_aus_datei,
    wert_aus_pfad,
)

PFLICHTSCHLUESSEL = {
    "projekt": "pfad",
    "abfrage": "frage",
    "berechnet": "formel",
    "fest": "wert",
    "vertrag": "suchhinweis",
}


def pruefe(ordner: Path, projekt: dict | None) -> tuple[list[str], list[str]]:
    fehler: list[str] = []
    hinweise: list[str] = []

    meta = lade_vorlage(ordner)
    felder = meta.get("felder", [])

    for pflicht in ("name", "dokumententyp"):
        if not meta.get(pflicht):
            fehler.append(f"felder.yaml: Angabe '{pflicht}' fehlt")

    gesehen: set[str] = set()
    for feld in felder:
        key = feld.get("key")
        if not key:
            fehler.append("Feld ohne 'key'")
            continue
        if key in gesehen:
            fehler.append(f"{key}: doppelt definiert")
        gesehen.add(key)

        quelle = feld.get("quelle")
        if quelle not in QUELLEN:
            fehler.append(f"{key}: unbekannte quelle {quelle!r}, erlaubt: {sorted(QUELLEN)}")
            continue
        noetig = PFLICHTSCHLUESSEL[quelle]
        if not feld.get(noetig):
            fehler.append(f"{key}: quelle '{quelle}' braucht die Angabe '{noetig}'")
        if not feld.get("label"):
            hinweise.append(f"{key}: kein 'label' – in der Abfrage steht dann der key")

    if not meta["_datei"].exists():
        fehler.append(f"Vorlagendatei fehlt: {meta['_datei']}")
        return fehler, hinweise

    texte = [text_aus_datei(meta["_datei"])]
    if meta["_mail"] and meta["_mail"].exists():
        texte.append(text_aus_datei(meta["_mail"]))

    verwendet: set[str] = set()
    bloecke: set[str] = set()
    for text in texte:
        verwendet |= platzhalter(text)
        bloecke |= blockschluessel(text)
    verwendet |= bloecke

    definiert = set(felder_nach_key(meta))
    for key in sorted(verwendet - definiert):
        fehler.append(f"{{{{{key}}}}} steht in der Vorlage, fehlt aber in felder.yaml")
    for key in sorted(definiert - verwendet):
        hinweise.append(f"{key}: in felder.yaml definiert, wird in der Vorlage nicht benutzt")

    if projekt is not None:
        for feld in felder:
            if feld.get("quelle") != "projekt" or not feld.get("pflicht", True):
                continue
            if wert_aus_pfad(projekt, feld.get("pfad", "")) in (None, ""):
                hinweise.append(
                    f"{feld['key']}: projekt.yaml liefert '{feld.get('pfad')}' nicht – wird abgefragt"
                )

    return fehler, hinweise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("vorlagen", nargs="+", type=Path)
    parser.add_argument("--projekt", help="Projektname oder -ordner zum Gegenprüfen")
    args = parser.parse_args()

    projekt = lade_yaml(projektordner(args.projekt) / "projekt.yaml") if args.projekt else None

    gesamt = 0
    for ordner in args.vorlagen:
        if not (ordner / "felder.yaml").exists():
            print(f"× {ordner}: keine felder.yaml")
            gesamt += 1
            continue
        fehler, hinweise = pruefe(ordner, projekt)
        zeichen = "×" if fehler else "✓"
        print(f"{zeichen} {ordner}")
        for eintrag in fehler:
            print(f"    Fehler:  {eintrag}")
        for eintrag in hinweise:
            print(f"    Hinweis: {eintrag}")
        gesamt += len(fehler)

    return 1 if gesamt else 0


if __name__ == "__main__":
    raise SystemExit(main())
