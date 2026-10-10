"""Tests für die Post ans Hotel: Zimmeranfrage und Kostenübernahme.

Was hier schiefgeht, geht an einen Fremden raus. Ein falscher Betrag in der
Kostenübernahme ist eine Zusage der Firma, ein fehlender Vergleichspreis kostet
Geld, ein Name zu viel im Cockpit ist eine Datenpanne.

    python3 -m unittest discover tests
"""

import json
import os
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "werkzeuge"))

import hotelpost  # noqa: E402

ABSENDER = {
    "name": "Erika Beispiel",
    "funktion": "Projektleitung",
    "telefon": "+49 1234 5678-0",
    "email": "beispiel@example.com",
    "firma": "Muster GmbH",
    "strasse": "Musterweg 1",
    "plz": "12345",
    "ort": "Musterstadt",
    "telefon_zentrale": "+49 1234 5678-0",
    "web": "www.example.com",
    "registergericht": "Amtsgericht Musterstadt",
    "hrb": "HRB 9999",
    "ust_id": "DE999999999",
    "geschaeftsfuehrung": "Max Mustermann, Eva Musterfrau",
    "rechnung_email": "rechnung@example.com",
}
KRITERIEN = {"absender": ABSENDER, "pauschale_ab_naechten": 5}


def auftrag(naechte=3, zimmer=2, fahrzeuge=1, besetzung=None):
    return {
        "baustelle": {
            "kuerzel": "LNS",
            "kurzname": "Lidl Neckarsulm",
            "projektnummer": "",
            "ort": "Neckarsulm",
        },
        "zeitraum": {
            "anreise": "13.10.2026",
            "abreise": "16.10.2026",
            "anreise_iso": "2026-10-13",
            "naechte": naechte,
        },
        "zimmer": zimmer,
        "fahrzeuge": fahrzeuge,
        "suche": {"fruehstueck_ab": "06:00"},
        "besetzung": besetzung
        if besetzung is not None
        else [{"kuerzel": "KH", "name": "Karl Beispiel", "fahrzeug": "Sprinter"}],
        "pauschale_erfragen": naechte >= 5,
    }


class Zahlen(unittest.TestCase):
    def test_euro_deutsch(self):
        self.assertEqual(hotelpost.euro(1234.5), "1.234,50")
        self.assertEqual(hotelpost.euro(88), "88,00")

    def test_betreff_wird_abgetrennt(self):
        betreff, text = hotelpost.mail_zerlegen("Betreff: Hallo\n\nText\n")
        self.assertEqual(betreff, "Hallo")
        self.assertTrue(text.startswith("Text"))


class Anfrage(unittest.TestCase):
    def test_vergleichspreis_steht_drin_wenn_bekannt(self):
        _, text = hotelpost.anfrage(auftrag(), KRITERIEN, vergleichspreis=94)
        self.assertIn("94,00 EUR je Zimmer und Nacht", text)
        self.assertIn("direkt bei Ihnen buchen", text)

    def test_ohne_vergleichspreis_kein_halber_satz(self):
        _, text = hotelpost.anfrage(auftrag(), KRITERIEN)
        self.assertNotIn("Online liegt der Preis", text)
        self.assertNotIn("{{", text)

    def test_ein_sprinter_fuer_zwei_mann_ist_ein_stellplatz(self):
        _, text = hotelpost.anfrage(auftrag(zimmer=2, fahrzeuge=1), KRITERIEN)
        self.assertIn("für 1 Fahrzeug,", text)

    def test_mehrzahl_bei_mehreren_fahrzeugen(self):
        _, text = hotelpost.anfrage(auftrag(zimmer=3, fahrzeuge=3), KRITERIEN)
        self.assertIn("für 3 Fahrzeuge,", text)

    def test_keine_fahrzeugart_in_der_mail(self):
        """Diana prüft die Zufahrt selbst. Die Mail nennt keine Fahrzeugart."""
        _, text = hotelpost.anfrage(auftrag(), KRITERIEN)
        self.assertNotIn("Sprinter", text)
        self.assertNotIn("Höhe", text)

    def test_fruehstueck_zum_mitnehmen_wird_erfragt(self):
        _, text = hotelpost.anfrage(auftrag(), KRITERIEN)
        self.assertIn("ab 06:00 Uhr", text)
        self.assertIn("Frühstück zum Mitnehmen", text)

    def test_signatur_mit_firmenmail(self):
        _, text = hotelpost.anfrage(auftrag(), KRITERIEN)
        self.assertIn("beispiel@example.com", text)
        self.assertIn("Musterweg 1, 12345 Musterstadt", text)

    def test_fehlende_telefonnummer_hinterlaesst_kein_tel_ohne_nummer(self):
        kriterien = {"absender": dict(ABSENDER, telefon="")}
        _, text = hotelpost.anfrage(auftrag(), kriterien)
        self.assertNotIn("Tel. \n", text)
        self.assertFalse(text.rstrip().endswith("Tel."))

    def test_betreff_nennt_zeitraum_und_zimmer(self):
        betreff, _ = hotelpost.anfrage(auftrag(), KRITERIEN)
        self.assertIn("13.10.2026 bis 16.10.2026", betreff)
        self.assertIn("2 Einzelzimmer", betreff)


class Kostenuebernahme(unittest.TestCase):
    def _erzeuge(self, **kw):
        werte = dict(
            hotel="Hotel Villa Sulmana",
            preis=88.0,
            gaeste=["Karl Beispiel", "Emil Beispiel"],
            bestaetigung="VS-1013",
            kriterien=KRITERIEN,
            datum=date(2026, 10, 10),
        )
        werte.update(kw)
        return hotelpost.kostenuebernahme(auftrag(), **werte)

    def test_gesamt_ist_zimmer_mal_naechte_mal_preis(self):
        self.assertEqual(self._erzeuge()["gesamt"], 528.0)
        self.assertIn("528,00 EUR", self._erzeuge()["html"])

    def test_parkgebuehr_je_fahrzeug_kommt_dazu(self):
        ergebnis = self._erzeuge(parkplatz_je_nacht=8.0)
        # 2 Zimmer x 3 Nächte x 88 plus 1 Fahrzeug x 3 Nächte x 8
        self.assertEqual(ergebnis["gesamt"], 528.0 + 24.0)

    def test_falsche_gaestezahl_wird_gemeldet(self):
        ergebnis = self._erzeuge(gaeste=["Karl Beispiel"])
        self.assertTrue(any("1 Gäste für 2 Zimmer" in h for h in ergebnis["hinweise"]))

    def test_hotelname_mit_sonderzeichen_wird_maskiert(self):
        ergebnis = self._erzeuge(hotel="Rössle & <Post>")
        self.assertIn("Rössle &amp; &lt;Post&gt;", ergebnis["html"])
        self.assertNotIn("<Post>", ergebnis["html"])

    def test_fehlendes_registergericht_wird_gemeldet(self):
        kriterien = {"absender": dict(ABSENDER, registergericht="")}
        ergebnis = self._erzeuge(kriterien=kriterien)
        self.assertTrue(any("Registergericht" in h for h in ergebnis["hinweise"]))

    def test_vollstaendige_angaben_ohne_hinweis(self):
        self.assertEqual(self._erzeuge()["hinweise"], [])

    def test_pflichtangaben_stehen_im_fuss(self):
        doc = self._erzeuge()["html"]
        for angabe in ("Amtsgericht Musterstadt", "HRB 9999", "DE999999999",
                       "Max Mustermann, Eva Musterfrau", "Sitz: Musterstadt"):
            self.assertIn(angabe, doc)

    def test_rechnung_geht_an_die_rechnungsadresse(self):
        ergebnis = self._erzeuge()
        self.assertIn("rechnung@example.com", ergebnis["text"])
        self.assertIn("rechnung@example.com", ergebnis["html"])

    def test_berufliche_veranlassung_steht_drin(self):
        """Befreit in vielen Städten von der Übernachtungsteuer."""
        self.assertIn("aus beruflichen Gründen", self._erzeuge()["html"])

    def test_keine_platzhalter_bleiben_stehen(self):
        ergebnis = self._erzeuge()
        self.assertNotIn("{{", ergebnis["html"])
        self.assertNotIn("{{", ergebnis["text"])

    def test_schrift_ist_eingebettet(self):
        doc = self._erzeuge()["html"]
        self.assertEqual(doc.count("data:font/woff;base64,"), 2)
        self.assertNotIn("fonts.googleapis.com", doc)

    def test_dateiname_ohne_sonderzeichen(self):
        name = self._erzeuge(hotel="Gasthof Zum Rössle & Post")["dateiname"]
        self.assertTrue(all(z.isalnum() or z in "_-" for z in name), name)
        self.assertIn("LNS", name)
        self.assertIn("2026-10-13", name)

    def test_ohne_unterschriftsbild_der_vermerk(self):
        self.assertIn("ohne Unterschrift gültig", self._erzeuge()["html"])

    def test_betreff_mit_buchungsnummer(self):
        self.assertIn("Buchung VS-1013", self._erzeuge()["betreff"])


class CockpitOhneAbsender(unittest.TestCase):
    """Das Cockpit wird als Webseite veröffentlicht. Name, Durchwahl und
    Mailadresse aus dem Absender haben darin nichts verloren."""

    def test_absender_landet_nicht_im_cockpit(self):
        import cockpit
        import hotels

        with tempfile.TemporaryDirectory() as tmp:
            ordner = Path(tmp) / "hotels"
            ordner.mkdir()
            (ordner / "baustellen.yaml").write_text(
                "baustellen:\n  - kuerzel: T\n    kurzname: Test\n"
                "    koordinaten: {lat: 50.0, lon: 9.0}\n", encoding="utf-8")
            (ordner / "monteure.yaml").write_text(
                "monteure:\n  - kuerzel: A\n    name: Anton\n", encoding="utf-8")
            (ordner / "kriterien.yaml").write_text(
                "absender:\n  name: Geheim Person\n  email: geheim@example.com\n"
                "  telefon: '0661 999'\n", encoding="utf-8")
            alt = os.environ.get("VORLAGENMANAGER_DATEN")
            os.environ["VORLAGENMANAGER_DATEN"] = tmp
            try:
                ziel = cockpit.erzeuge(Path(tmp) / "c.html")
                inhalt = Path(ziel).read_text(encoding="utf-8")
            finally:
                if alt is None:
                    os.environ.pop("VORLAGENMANAGER_DATEN")
                else:
                    os.environ["VORLAGENMANAGER_DATEN"] = alt
        self.assertNotIn("geheim@example.com", inhalt)
        self.assertNotIn("Geheim Person", inhalt)
        self.assertNotIn("0661 999", inhalt)


class Vorlauf(unittest.TestCase):
    """Direkt beim Hotel ist Standard, außer die Anreise ist zu nah."""

    def _auftrag(self, tage_bis_anreise):
        import argparse
        import hotelsuche

        von = date.today() + timedelta(days=tage_bis_anreise)
        bis = von + timedelta(days=2)
        with tempfile.TemporaryDirectory() as tmp:
            ordner = Path(tmp) / "hotels"
            ordner.mkdir()
            (ordner / "baustellen.yaml").write_text(
                "baustellen:\n  - kuerzel: T\n    kurzname: Test\n"
                "    koordinaten: {lat: 50.0, lon: 9.0}\n", encoding="utf-8")
            (ordner / "monteure.yaml").write_text(
                "monteure:\n  - kuerzel: A\n    name: Anton\n", encoding="utf-8")
            alt = os.environ.get("VORLAGENMANAGER_DATEN")
            os.environ["VORLAGENMANAGER_DATEN"] = tmp
            try:
                args = argparse.Namespace(
                    baustelle="T", von=von.strftime("%d.%m.%Y"),
                    bis=bis.strftime("%d.%m.%Y"), monteure=["A"], zimmer=None,
                    fahrzeuge=None,
                )
                return hotelsuche._auftrag_bauen(args)
            finally:
                if alt is None:
                    os.environ.pop("VORLAGENMANAGER_DATEN")
                else:
                    os.environ["VORLAGENMANAGER_DATEN"] = alt

    def test_eine_woche_vorlauf_direkt(self):
        self.assertTrue(self._auftrag(7)["direktbuchung"])

    def test_anreise_heute_portal_oder_anruf(self):
        self.assertFalse(self._auftrag(0)["direktbuchung"])

    def test_ohne_angabe_ein_fahrzeug_je_mann(self):
        self.assertEqual(self._auftrag(7)["fahrzeuge"], 1)


if __name__ == "__main__":
    unittest.main()
