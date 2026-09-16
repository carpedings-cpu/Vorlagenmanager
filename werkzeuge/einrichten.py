#!/usr/bin/env python3
"""Legt fest, wo die Projektdaten liegen – außerhalb des Repos.

    python3 werkzeuge/einrichten.py ~/Desktop/Vorlagenmanager-Daten

Legt den Ordner mit projekte/, ausgang/ und hotels/ an und merkt sich den Pfad
in `.datenpfad`. Diese Merkdatei wird nicht eingecheckt, der Pfad bleibt also
auf deinem Rechner.

Ohne Argument wird der aktuell eingestellte Pfad angezeigt.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from kern import datenwurzel, repowurzel  # noqa: E402


def main() -> int:
    wurzel = repowurzel()

    if len(sys.argv) == 1:
        aktuell = datenwurzel()
        print(f"Datenordner: {aktuell}")
        if aktuell == wurzel:
            print("(noch nicht gesetzt – Daten lägen im Repo)")
        return 0

    if len(sys.argv) != 2:
        print(__doc__)
        return 1

    ziel = Path(sys.argv[1]).expanduser().resolve()
    (ziel / "projekte").mkdir(parents=True, exist_ok=True)
    (ziel / "ausgang").mkdir(parents=True, exist_ok=True)
    (ziel / "hotels").mkdir(parents=True, exist_ok=True)

    musterziel = ziel / "projekte" / "_vorlage_projekt.yaml"
    if not musterziel.exists():
        shutil.copy(wurzel / "projekte" / "_vorlage_projekt.yaml", musterziel)

    # Stammdaten der Hotelsuche: Vorlage einmalig kopieren, dann in Ruhe lassen.
    # Ein zweiter Aufruf darf ausgefüllte Baustellen nicht überschreiben.
    for vorlage, angelegt in (
        ("_vorlage_baustellen.yaml", "baustellen.yaml"),
        ("_vorlage_monteure.yaml", "monteure.yaml"),
    ):
        hotelziel = ziel / "hotels" / angelegt
        if not hotelziel.exists():
            shutil.copy(wurzel / "stammdaten" / vorlage, hotelziel)

    (wurzel / ".datenpfad").write_text(f"{ziel}\n", encoding="utf-8")

    print(f"Datenordner: {ziel}")
    print(f"  {ziel / 'projekte'}   ← projekt.yaml je Projekt, dazu vertrag/")
    print(f"  {ziel / 'ausgang'}    ← die fertigen Schreiben")
    print(f"  {ziel / 'hotels'}     ← baustellen.yaml, monteure.yaml, buchungen.yaml")
    print("\nGemerkt in .datenpfad. Diese Datei wird nicht eingecheckt.")
    print("\nIn hotels/ liegen jetzt die Beispiel-Stammdaten. Die echten")
    print("Baustellen und Monteure dort eintragen, dann läuft die Hotelsuche.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
