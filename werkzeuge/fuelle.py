#!/usr/bin/env python3
"""Füllt eine Vorlage mit Projekt- und Fallwerten und schreibt sie nach ausgang/.

Welche Felder noch offen sind, also abgefragt oder aus den Vertragsdateien
geholt werden müssen:

    python3 werkzeuge/fuelle.py vorlagen/bedenkenanmeldung projekte/2451_klinikum --offen

Generieren, sobald die Werte in einer JSON-Datei stehen:

    python3 werkzeuge/fuelle.py vorlagen/bedenkenanmeldung projekte/2451_klinikum \
        --werte werte.json --stichwort "Ausgabetheke"

Ohne --erzwingen bricht das Skript ab, solange Pflichtfelder leer sind. Das ist
Absicht: ein Schreiben mit leerer Frist soll nicht versehentlich entstehen.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from kern import (  # noqa: E402
    datenwurzel,
    ersetze_in_docx,
    ersetze_in_markdown,
    felder_nach_key,
    lade_vorlage,
    lade_yaml,
    projektordner,
    sammle_werte,
)

def dateiname(meta: dict, projekt: dict, stichwort: str | None) -> str:
    """Benennung nach VA 1.3: Datum_Projektnummer_Dokumententyp_Stichwort."""
    teile = [
        date.today().strftime("%Y-%m-%d"),
        str(projekt.get("projektnummer", "")).strip(),
        str(meta.get("dokumententyp", meta.get("name", "Schreiben"))).strip(),
    ]
    if stichwort:
        teile.append(stichwort.strip())
    sauber = [re.sub(r"[^\wäöüÄÖÜß.-]+", "-", t).strip("-") for t in teile if t]
    return "_".join(sauber)


def offene_felder(meta: dict, offen: list[str]) -> list[dict]:
    felder = felder_nach_key(meta)
    ausgabe = []
    for key in offen:
        feld = felder[key]
        eintrag = {
            "key": key,
            "label": feld.get("label", key),
            "quelle": feld.get("quelle"),
            "typ": feld.get("typ", "text"),
        }
        for optional in ("frage", "beispiel", "auswahl", "suchhinweis", "dateien"):
            if feld.get(optional):
                eintrag[optional] = feld[optional]
        ausgabe.append(eintrag)
    return ausgabe


def schreibe_mail(meta: dict, werte: dict, ziel: Path) -> Path | None:
    if not meta["_mail"] or not meta["_mail"].exists():
        return None
    roh = meta["_mail"].read_text(encoding="utf-8")
    gefuellt = ersetze_in_markdown(roh, werte)
    ziel.write_text(gefuellt, encoding="utf-8")
    return ziel


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("vorlage", type=Path)
    parser.add_argument("projekt", help="Projektname oder Pfad zum Projektordner")
    parser.add_argument("--werte", type=Path, help="JSON mit den ermittelten Werten")
    parser.add_argument("--offen", action="store_true", help="offene Felder als JSON ausgeben")
    parser.add_argument("--stichwort", help="Stichwort für den Dateinamen")
    parser.add_argument("--ausgabe", type=Path, help="Zielordner, sonst ausgang/<projekt>/")
    parser.add_argument("--erzwingen", action="store_true", help="auch bei offenen Pflichtfeldern")
    args = parser.parse_args()

    meta = lade_vorlage(args.vorlage)
    ordner = projektordner(args.projekt)
    projekt = lade_yaml(ordner / "projekt.yaml")
    vorgaben = json.loads(args.werte.read_text(encoding="utf-8")) if args.werte else {}

    werte, offen = sammle_werte(meta, projekt, vorgaben)

    if args.offen:
        print(json.dumps(offene_felder(meta, offen), ensure_ascii=False, indent=2))
        return 0

    if offen and not args.erzwingen:
        felder = felder_nach_key(meta)
        print("Noch offen – erst klären, dann generieren:", file=sys.stderr)
        for key in offen:
            print(f"  {key}: {felder[key].get('label', key)}", file=sys.stderr)
        return 1

    zielordner = args.ausgabe or datenwurzel() / "ausgang" / ordner.name
    zielordner.mkdir(parents=True, exist_ok=True)
    basis = dateiname(meta, projekt, args.stichwort)

    endung = meta["_datei"].suffix.lower()
    ziel = zielordner / f"{basis}{endung}"
    if endung == ".docx":
        ersetze_in_docx(meta["_datei"], ziel, werte)
    else:
        ziel.write_text(
            ersetze_in_markdown(meta["_datei"].read_text(encoding="utf-8"), werte),
            encoding="utf-8",
        )
    print(ziel)

    mail = schreibe_mail(meta, werte, zielordner / f"{basis}_Mail.md")
    if mail:
        print(mail)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
