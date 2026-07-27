#!/usr/bin/env python3
"""Legt einen Projektordner aus der Vorlage an.

    python3 werkzeuge/neues_projekt.py 2451 "Klinikum Beispielstadt"

Danach die projekt.yaml ausfüllen und gegenprüfen:

    python3 werkzeuge/pruefe_vorlage.py vorlagen/*/ --projekt projekte/2451_klinikum-beispielstadt
"""

from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from kern import datenwurzel, repowurzel  # noqa: E402

UMLAUTE = {"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"}


def schluessel(text: str) -> str:
    text = text.lower()
    for zeichen, ersatz in UMLAUTE.items():
        text = text.replace(zeichen, ersatz)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 1

    nummer, kurzname = sys.argv[1], sys.argv[2]
    ziel = datenwurzel() / "projekte" / f"{nummer}_{schluessel(kurzname)}"

    if ziel.exists():
        print(f"Gibt es schon: {ziel}", file=sys.stderr)
        return 1

    muster = repowurzel() / "projekte" / "_vorlage_projekt.yaml"
    vorlage = muster.read_text(encoding="utf-8")
    vorlage = vorlage.replace('projektnummer: ""', f'projektnummer: "{nummer}"')
    vorlage = vorlage.replace('kurzname: ""', f'kurzname: "{kurzname}"')

    (ziel / "vertrag").mkdir(parents=True)
    (ziel / "vertrag" / ".gitkeep").touch()
    (ziel / "projekt.yaml").write_text(vorlage, encoding="utf-8")

    print(ziel / "projekt.yaml")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
