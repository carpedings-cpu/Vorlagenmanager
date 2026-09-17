"""Tests für den Cockpit-Generator.

Hier bleibt ein Fehler besonders still: Eine HTML-Datei sieht fertig aus,
auch wenn die Stammdaten gar nicht drinstehen. Dann steht das Dropdown leer
auf der Baustelle und keiner weiß, warum.

    python3 -m unittest discover tests
"""

import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "werkzeuge"))

import cockpit  # noqa: E402

BAUSTELLEN = """
baustellen:
  - kuerzel: UPB
    kurzname: Upbeat Berlin
    strasse: Heidestraße 26
    plz: "10557"
    ort: Berlin
    koordinaten: {lat: 52.5368, lon: 13.3602}
    max_entfernung_km: 8
    max_preis_pro_nacht: 220
    hinweis: "Testhinweis"
  - kuerzel: OHNE
    kurzname: Ohne Koordinaten
    ort: Nirgendwo
"""

MONTEURE = """
monteure:
  - kuerzel: MS
    name: Milenko Stanic
    fahrzeug: Sprinter
  - kuerzel: ZI
    name: Diana Ziegler
    buero: true
"""


class Generator(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        ordner = Path(self.tmp.name) / "hotels"
        ordner.mkdir(parents=True)
        (ordner / "baustellen.yaml").write_text(BAUSTELLEN, encoding="utf-8")
        (ordner / "monteure.yaml").write_text(MONTEURE, encoding="utf-8")
        self.alt = os.environ.get("VORLAGENMANAGER_DATEN")
        os.environ["VORLAGENMANAGER_DATEN"] = self.tmp.name

    def tearDown(self):
        os.environ.pop("VORLAGENMANAGER_DATEN", None)
        if self.alt is not None:
            os.environ["VORLAGENMANAGER_DATEN"] = self.alt
        self.tmp.cleanup()

    def _erzeugen(self):
        ziel = Path(self.tmp.name) / "cockpit.html"
        cockpit.erzeuge(ziel)
        return ziel.read_text(encoding="utf-8")

    def test_kein_platzhalter_bleibt_stehen(self):
        self.assertNotIn("{{", self._erzeugen())

    def test_stammdaten_stehen_wirklich_drin(self):
        text = self._erzeugen()
        self.assertIn("Upbeat Berlin", text)
        self.assertIn("Milenko Stanic", text)

    def test_baustelle_ohne_koordinaten_wird_uebersprungen(self):
        # Sie würde die Suche sonst auf Punkt null schicken
        text = self._erzeugen()
        treffer = re.search(r"const BAUSTELLEN\s*=\s*(\[.*?\]);", text, re.S)
        self.assertIsNotNone(treffer)
        baustellen = json.loads(treffer.group(1))
        self.assertEqual([b["kuerzel"] for b in baustellen], ["UPB"])

    def test_eigenes_preislimit_kommt_mit(self):
        text = self._erzeugen()
        treffer = re.search(r"const BAUSTELLEN\s*=\s*(\[.*?\]);", text, re.S)
        self.assertEqual(json.loads(treffer.group(1))[0]["max_preis_pro_nacht"], 220)

    def test_buero_wird_als_solches_markiert(self):
        text = self._erzeugen()
        treffer = re.search(r"const MONTEURE\s*=\s*(\[.*?\]);", text, re.S)
        leute = {m["kuerzel"]: m for m in json.loads(treffer.group(1))}
        self.assertTrue(leute["ZI"]["buero"])
        self.assertFalse(leute["MS"]["buero"])

    def test_umlaute_bleiben_lesbar(self):
        # ensure_ascii würde aus Heidestraße ß machen - im Quelltext
        # unlesbar und beim Vergleichen lästig
        self.assertIn("Heidestraße 26", self._erzeugen())

    def test_fehlende_stammdaten_melden_sich(self):
        os.environ["VORLAGENMANAGER_DATEN"] = tempfile.mkdtemp()
        with self.assertRaises(FileNotFoundError):
            cockpit.erzeuge(Path(self.tmp.name) / "x.html")


if __name__ == "__main__":
    unittest.main()
