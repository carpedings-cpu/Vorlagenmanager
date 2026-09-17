"""Regressionstests für die Hotelsuche.

Abgesichert ist, was still falsch sein kann: eine Entfernung, die stimmt,
aber zum falschen Punkt gerechnet wird, ein Parkhaus, das als Stellplatz
durchgeht, ein Nachtpreis, der Zimmer und Nächte verwechselt. Am Ende steht
ein Mann abends vor dem falschen Haus.

    python3 -m unittest discover tests
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "werkzeuge"))

from hotels import (  # noqa: E402
    Treffer,
    auswerten,
    beurteile_parkplatz,
    einsatzkosten,
    kostentabelle,
    finde_baustelle,
    finde_monteure,
    fahrzeit_minuten,
    luftlinie_km,
    naechte,
    uebersicht,
)

# Bremerhaven, Umfeld der Innenstadt. Reale Koordinaten, damit die
# Entfernungen prüfbar bleiben.
BAUSTELLE = {
    "kuerzel": "BHV",
    "kurzname": "Carl Zeiss Bremerhaven",
    "koordinaten": {"lat": 53.5396, "lon": 8.5809},
    "max_entfernung_km": 8,
}

KRITERIEN = {
    "max_entfernung_km": 8,
    "mindestbewertung": 8.0,
    "mindestanzahl_bewertungen": 50,
    "max_preis_pro_nacht": 120,
    "parkplatz_pflicht": True,
    "gewicht_entfernung": 40,
    "gewicht_preis": 30,
    "gewicht_bewertung": 20,
    "gewicht_parken": 10,
}


def hotel(name, lat, lon, preis, bewertung=8.5, ausstattung=None, anzahl=500, hid=1):
    return {
        "id": hid,
        "name": name,
        "url": f"https://example.invalid/{hid}",
        "price": {"book": preis, "currency": "EUR"},
        "rating": {"review_score": bewertung, "number_of_reviews": anzahl, "stars": 3},
        "facilities": ausstattung if ausstattung is not None else ["Privatparkplatz"],
        "location": {
            "address": "Teststraße 1",
            "city_name": "Bremerhaven",
            "postal_code": "27568",
            "coordinates": {"latitude": lat, "longitude": lon},
        },
    }


class Entfernung(unittest.TestCase):
    def test_luftlinie_gegen_bekannten_wert(self):
        # Bremerhaven -> Bremen, rund 53 km Luftlinie
        km = luftlinie_km(53.5396, 8.5809, 53.0793, 8.8017)
        self.assertAlmostEqual(km, 53, delta=2)

    def test_gleicher_punkt_ist_null(self):
        self.assertAlmostEqual(luftlinie_km(53.5, 8.5, 53.5, 8.5), 0.0, places=6)

    def test_fahrzeit_waechst_mit_der_entfernung(self):
        self.assertLess(fahrzeit_minuten(2), fahrzeit_minuten(20))

    def test_naechte_zaehlt_uebernachtungen_nicht_tage(self):
        # Mo an, Fr ab: vier Übernachtungen, nicht fünf Tage
        self.assertEqual(naechte("12.10.2026", "16.10.2026"), 4)

    def test_naechte_versteht_auch_iso(self):
        self.assertEqual(naechte("2026-10-12", "2026-10-16"), 4)

    def test_unsinniges_datum_fliegt_auf(self):
        with self.assertRaises(ValueError):
            naechte("übermorgen", "16.10.2026")


class Parkplatz(unittest.TestCase):
    """Die Ausstattungsliste sagt nur, ob es einen Stellplatz gibt."""

    def test_privatparkplatz_zaehlt_als_eigener_stellplatz(self):
        urteil = beurteile_parkplatz(["Privatparkplatz", "Parken vor Ort"])
        self.assertEqual(urteil.status, "ok")

    def test_parkhaus_zaehlt_auch_als_stellplatz(self):
        # Ob das Fahrzeug hineinpasst, klärt Diana beim Haus
        self.assertEqual(beurteile_parkplatz(["Parkplatz", "Parkhaus"]).status, "ok")

    def test_strassenparken_ist_kein_stellplatz(self):
        urteil = beurteile_parkplatz(["Parkplätze an der Straße"])
        self.assertEqual(urteil.status, "kritisch")

    def test_ohne_angabe_kein_parkplatz(self):
        self.assertEqual(beurteile_parkplatz([]).status, "kritisch")

    def test_unklare_angabe_wird_zum_nachfragen(self):
        self.assertEqual(beurteile_parkplatz(["Parkplatz"]).status, "pruefen")

class Auswertung(unittest.TestCase):
    def test_nachtpreis_teilt_durch_zimmer_und_naechte(self):
        # 1440 EUR für 3 Zimmer über 4 Nächte sind 120 EUR je Zimmer und Nacht
        treffer = auswerten(
            [hotel("Test", 53.5400, 8.5810, 1440)],
            BAUSTELLE,
            zimmer=3,
            anzahl_naechte=4,
            kriterien=KRITERIEN,
        )
        self.assertAlmostEqual(treffer[0].preis_pro_nacht, 120.0, places=2)

    def test_zu_weit_weg_fliegt_raus(self):
        treffer = auswerten(
            [hotel("Weit weg", 53.0793, 8.8017, 400)],
            BAUSTELLE,
            zimmer=1,
            anzahl_naechte=4,
            kriterien=KRITERIEN,
        )
        self.assertFalse(treffer[0].geeignet)
        self.assertIn("km", treffer[0].ausschluss)

    def test_schlechte_bewertung_fliegt_raus(self):
        treffer = auswerten(
            [hotel("Mäßig", 53.5400, 8.5810, 300, bewertung=7.2)],
            BAUSTELLE,
            zimmer=1,
            anzahl_naechte=4,
            kriterien=KRITERIEN,
        )
        self.assertFalse(treffer[0].geeignet)
        self.assertIn("Bewertung", treffer[0].ausschluss)

    def test_wenige_bewertungen_fliegen_raus(self):
        treffer = auswerten(
            [hotel("Frisch eröffnet", 53.5400, 8.5810, 300, bewertung=9.8, anzahl=3)],
            BAUSTELLE,
            zimmer=1,
            anzahl_naechte=4,
            kriterien=KRITERIEN,
        )
        self.assertFalse(treffer[0].geeignet)

    def test_ausschlussgrund_steht_dabei_statt_still_zu_verschwinden(self):
        treffer = auswerten(
            [hotel("Teuer", 53.5400, 8.5810, 2000)],
            BAUSTELLE,
            zimmer=1,
            anzahl_naechte=4,
            kriterien=KRITERIEN,
        )
        self.assertTrue(treffer[0].ausschluss)

    def test_naeheres_hotel_steht_bei_sonst_gleichen_werten_vorn(self):
        nah = hotel("Nah", 53.5400, 8.5810, 400, hid=1)
        fern = hotel("Fern", 53.5800, 8.6300, 400, hid=2)
        treffer = auswerten(
            [fern, nah], BAUSTELLE, zimmer=1, anzahl_naechte=4, kriterien=KRITERIEN
        )
        self.assertEqual(treffer[0].name, "Nah")

    def test_guenstiger_gewinnt_bei_gleicher_lage(self):
        teuer = hotel("Teuer", 53.5400, 8.5810, 470, hid=1)
        billig = hotel("Günstig", 53.5400, 8.5810, 300, hid=2)
        treffer = auswerten(
            [teuer, billig], BAUSTELLE, zimmer=1, anzahl_naechte=4, kriterien=KRITERIEN
        )
        self.assertEqual(treffer[0].name, "Günstig")

    def test_geeignete_stehen_immer_vor_den_aussortierten(self):
        gut = hotel("Passt", 53.5400, 8.5810, 400, hid=1)
        raus = hotel("Passt nicht", 53.5400, 8.5810, 400, bewertung=6.0, hid=2)
        treffer = auswerten(
            [raus, gut], BAUSTELLE, zimmer=1, anzahl_naechte=4, kriterien=KRITERIEN
        )
        self.assertEqual(treffer[0].name, "Passt")

    def test_baustelle_ohne_koordinaten_bricht_ab(self):
        ohne = {"kurzname": "Ohne Koordinaten", "koordinaten": {}}
        with self.assertRaises(ValueError) as ctx:
            auswerten([hotel("Egal", 53.54, 8.58, 300)], ohne, 1, 4, KRITERIEN)
        self.assertIn("Koordinaten", str(ctx.exception))

    def test_uebersicht_nennt_den_grund_wenn_nichts_passt(self):
        treffer = auswerten(
            [hotel("Zu teuer", 53.5400, 8.5810, 2000)],
            BAUSTELLE,
            zimmer=1,
            anzahl_naechte=4,
            kriterien=KRITERIEN,
        )
        text = uebersicht(treffer)
        self.assertIn("Zu teuer", text)
        self.assertIn("kriterien.yaml", text)


class Stammdaten(unittest.TestCase):
    BAUSTELLEN = [
        {"kuerzel": "BHV", "kurzname": "Carl Zeiss Bremerhaven", "ort": "Bremerhaven"},
        {"kuerzel": "BER", "kurzname": "Upbeat Berlin", "ort": "Berlin"},
        {"kuerzel": "BERN", "kurzname": "Bernhard Klinik", "ort": "Bernkastel"},
    ]
    MONTEURE = [
        {"kuerzel": "MK", "name": "Max Mustermann", "fahrzeug": "Sprinter"},
        {"kuerzel": "TS", "name": "Thomas Schmitt", "fahrzeug": "PKW"},
    ]

    def test_kuerzel_findet_die_baustelle(self):
        gefunden = finde_baustelle("BHV", self.BAUSTELLEN)
        self.assertEqual(gefunden["kurzname"], "Carl Zeiss Bremerhaven")

    def test_kleinschreibung_und_umlaute_sind_egal(self):
        gefunden = finde_baustelle("bremerhaven", self.BAUSTELLEN)
        self.assertEqual(gefunden["kuerzel"], "BHV")

    def test_exaktes_kuerzel_schlaegt_teiltreffer(self):
        # "BER" steckt auch in "Bernhard Klinik" - das Kürzel muss gewinnen
        self.assertEqual(finde_baustelle("BER", self.BAUSTELLEN)["kuerzel"], "BER")

    def test_unbekannte_baustelle_nennt_die_vorhandenen(self):
        with self.assertRaises(LookupError) as ctx:
            finde_baustelle("Hintertupfingen", self.BAUSTELLEN)
        self.assertIn("Upbeat Berlin", str(ctx.exception))

    def test_monteure_ueber_kuerzel(self):
        gefunden = finde_monteure(["MK", "TS"], self.MONTEURE)
        self.assertEqual([m["kuerzel"] for m in gefunden], ["MK", "TS"])

    def test_monteure_auch_ueber_den_namen(self):
        gefunden = finde_monteure(["Mustermann"], self.MONTEURE)
        self.assertEqual(gefunden[0]["kuerzel"], "MK")

    def test_unbekannter_monteur_wird_gemeldet(self):
        with self.assertRaises(LookupError) as ctx:
            finde_monteure(["XY"], self.MONTEURE)
        self.assertIn("XY", str(ctx.exception))

    def test_fehlende_stammdatei_sagt_wie_es_weitergeht(self):
        from hotels import lade_baustellen

        with tempfile.TemporaryDirectory() as tmp:
            alt = os.environ.get("VORLAGENMANAGER_DATEN")
            os.environ["VORLAGENMANAGER_DATEN"] = tmp
            try:
                with self.assertRaises(FileNotFoundError) as ctx:
                    lade_baustellen()
                self.assertIn("einrichten.py", str(ctx.exception))
            finally:
                os.environ.pop("VORLAGENMANAGER_DATEN")
                if alt is not None:
                    os.environ["VORLAGENMANAGER_DATEN"] = alt


if __name__ == "__main__":
    unittest.main()


class RankingGegenDenPreis(unittest.TestCase):
    """Vier Euro Ersparnis dürfen acht Kilometer Anfahrt nicht aufwiegen."""

    def test_naeheres_hotel_gewinnt_bei_kleinem_preisunterschied(self):
        # Marburg, real: Hotel Weber 10,9 km für 82,50 gegen
        # Zur Burgruine 2,8 km für 86,50. Der Monteur fährt jeden Tag hin.
        weit = hotel("Weit weg", 50.79804, 8.923191, 660, bewertung=8.8, anzahl=112, hid=1)
        nah = hotel("Gleich um die Ecke", 50.759249, 8.792306, 692, bewertung=8.1, anzahl=133, hid=2)
        baustelle = {
            "kurzname": "Marburg",
            "koordinaten": {"lat": 50.7805, "lon": 8.7707},
            "max_entfernung_km": 12,
        }
        kriterien = dict(KRITERIEN, max_entfernung_km=12)
        treffer = auswerten([weit, nah], baustelle, zimmer=2, anzahl_naechte=4,
                            kriterien=kriterien)
        self.assertEqual(treffer[0].name, "Gleich um die Ecke")

    def test_deutlich_guenstiger_gewinnt_weiterhin(self):
        # Gegenprobe: Bei echtem Preisunterschied soll der Preis ziehen
        teuer_nah = hotel("Teuer und nah", 53.5400, 8.5810, 470, hid=1)
        billig_fern = hotel("Günstig, etwas weiter", 53.5600, 8.6000, 240, hid=2)
        treffer = auswerten([teuer_nah, billig_fern], BAUSTELLE, zimmer=1,
                            anzahl_naechte=4, kriterien=KRITERIEN)
        self.assertEqual(treffer[0].name, "Günstig, etwas weiter")


class FehlendeBewertung(unittest.TestCase):
    """Kein Bewertungsfeld heißt unbewertet, nicht mit 0,0 bewertet.

    Und unbewertet heißt nicht aussortiert: Ein neu eröffnetes Haus kann
    näher und billiger sein als alles, was schon Bewertungen gesammelt hat.
    """

    @staticmethod
    def _ohne_bewertung():
        roh = hotel("Neu eröffnet", 53.5400, 8.5810, 300)
        roh["rating"] = {}
        return roh

    def test_unbewertet_fliegt_nicht_raus(self):
        """Karlstadt: Das näheste und zweitbilligste Haus war unbewertet.

        Es fiel aus der Liste, ohne dass jemand es je gesehen hätte. Fehlende
        Bewertung ist keine schlechte Bewertung.
        """
        treffer = auswerten([self._ohne_bewertung()], BAUSTELLE, zimmer=1,
                            anzahl_naechte=4, kriterien=KRITERIEN)
        self.assertTrue(treffer[0].geeignet)
        self.assertEqual(treffer[0].ausschluss, "")
        self.assertFalse(treffer[0].hat_bewertung)

    def test_schlechte_bewertung_fliegt_weiter_raus(self):
        schlecht = hotel("Mies bewertet", 53.5400, 8.5810, 300, bewertung=6.2)
        treffer = auswerten([schlecht], BAUSTELLE, zimmer=1, anzahl_naechte=4,
                            kriterien=KRITERIEN)
        self.assertFalse(treffer[0].geeignet)
        self.assertIn("6.2", treffer[0].ausschluss)

    def test_unbewertet_liegt_hinter_jeder_belegten_bewertung(self):
        """Unterstellt wird das geforderte Minimum, nicht mehr.

        Der erste Anlauf gab unbewerteten Häusern die halbe Punktzahl. Das
        klingt konservativ, ist es aber nicht: Die Skala beginnt bei 7,0, und
        echte Treffer liegen zwischen 8,0 und 8,7. Ein unbewertetes Haus hätte
        damit mehr Bewertungspunkte bekommen als eines mit belegter 8,4.
        """
        ohne = self._ohne_bewertung()
        ohne["id"] = 1
        knapp = hotel("Knapp über der Schwelle", 53.5400, 8.5810, 300,
                      bewertung=8.1, hid=2)
        treffer = auswerten([ohne, knapp], BAUSTELLE, zimmer=1,
                            anzahl_naechte=4, kriterien=KRITERIEN)
        nach_id = {t.hotel_id: t for t in treffer}
        # Gleiche Lage, gleicher Preis, gleicher Parkplatz: Es entscheidet
        # allein die Bewertung, und die belegte 8,1 schlägt die unterstellte.
        self.assertGreater(nach_id[2].punkte, nach_id[1].punkte)

    def test_unbewertet_wird_nicht_auf_null_gesetzt(self):
        """Keine Strafe fürs Neueröffnen: Näher und billiger zählt weiter."""
        ohne = self._ohne_bewertung()
        ohne["id"] = 1
        weiter_und_teurer = hotel("Bewertet, aber weiter weg", 53.5700, 8.6200,
                                  480, bewertung=8.5, hid=2)
        treffer = auswerten([ohne, weiter_und_teurer], BAUSTELLE, zimmer=1,
                            anzahl_naechte=4, kriterien=KRITERIEN)
        self.assertEqual(treffer[0].hotel_id, 1)

    def test_hinweis_unter_der_tabelle_erklaert_die_luecke(self):
        treffer = auswerten([self._ohne_bewertung()], BAUSTELLE, zimmer=1,
                            anzahl_naechte=4, kriterien=KRITERIEN)
        text = uebersicht(treffer)
        self.assertIn("noch unbewertet", text)
        self.assertIn("Mindestbewertung", text)

    def test_bewertetes_haus_bleibt_unberuehrt(self):
        treffer = auswerten([hotel("Bewertet", 53.5400, 8.5810, 300, bewertung=8.5)],
                            BAUSTELLE, zimmer=1, anzahl_naechte=4, kriterien=KRITERIEN)
        self.assertTrue(treffer[0].hat_bewertung)
        self.assertTrue(treffer[0].geeignet)

    def test_tabelle_schreibt_ohne_bewertung_statt_null_komma_null(self):
        gut = hotel("Passt", 53.5400, 8.5810, 300, bewertung=8.5, hid=1)
        roh = self._ohne_bewertung()
        roh["id"] = 2
        treffer = auswerten([gut, roh], BAUSTELLE, zimmer=1, anzahl_naechte=4,
                            kriterien=dict(KRITERIEN, mindestbewertung=0,
                                           mindestanzahl_bewertungen=0))
        text = uebersicht(treffer)
        self.assertIn("ohne Bewertung", text)


class PreislimitJeBaustelle(unittest.TestCase):
    """Berlin braucht andere Zahlen als Marburg."""

    BERLIN = {
        "kurzname": "Upbeat Berlin",
        "koordinaten": {"lat": 52.5368, "lon": 13.3602},
        "max_entfernung_km": 8,
        "max_preis_pro_nacht": 160,
    }

    @staticmethod
    def _berliner_hotel(preis_gesamt):
        # 3 Zimmer, 4 Nächte
        return hotel("Berliner Haus", 52.5400, 13.3610, preis_gesamt, bewertung=8.5)

    def test_baustelle_hebt_das_limit_an(self):
        # 1740 EUR / 3 / 4 = 145 EUR, über den globalen 120, unter den 160 hier
        treffer = auswerten([self._berliner_hotel(1740)], self.BERLIN, zimmer=3,
                            anzahl_naechte=4, kriterien=KRITERIEN)
        self.assertTrue(treffer[0].geeignet, treffer[0].ausschluss)

    def test_ueber_dem_eigenen_limit_fliegt_trotzdem_raus(self):
        # 2040 / 3 / 4 = 170 EUR, auch über den 160 der Baustelle
        treffer = auswerten([self._berliner_hotel(2040)], self.BERLIN, zimmer=3,
                            anzahl_naechte=4, kriterien=KRITERIEN)
        self.assertFalse(treffer[0].geeignet)
        self.assertIn("160", treffer[0].ausschluss)

    def test_ohne_eigenen_wert_gilt_die_vorgabe(self):
        ohne = dict(self.BERLIN)
        del ohne["max_preis_pro_nacht"]
        treffer = auswerten([self._berliner_hotel(1740)], ohne, zimmer=3,
                            anzahl_naechte=4, kriterien=KRITERIEN)
        self.assertFalse(treffer[0].geeignet)
        self.assertIn("120", treffer[0].ausschluss)

    def test_null_als_eigener_wert_hebt_das_limit_auf(self):
        ohne_limit = dict(self.BERLIN, max_preis_pro_nacht=0)
        treffer = auswerten([self._berliner_hotel(3600)], ohne_limit, zimmer=3,
                            anzahl_naechte=4, kriterien=KRITERIEN)
        self.assertTrue(treffer[0].geeignet, treffer[0].ausschluss)


class PauschaleNurBeiLangenAufenthalten(unittest.TestCase):
    """Bei vier Nächten nach einer Wochenpauschale zu fragen wirkt unbedacht."""

    def _anfrage(self, naechte_zahl):
        from kern import ersetze_in_markdown, repowurzel

        werte = {
            "ort": "Oberursel",
            "anreise": "28.09.2026",
            "abreise": "02.10.2026",
            "naechte": str(naechte_zahl),
            "zimmer": "3",
            "fahrzeuge": "3",
            "fruehstueck_ab": "06:00",
            "pauschale": "ja" if naechte_zahl >= 5 else "",
            "hinweis": "",
            "absender": "Diana Ziegler",
            "firma": "KPC GmbH",
        }
        vorlage = repowurzel() / "vorlagen" / "hotelanfrage" / "anfrage.md"
        return ersetze_in_markdown(vorlage.read_text(encoding="utf-8"), werte)

    def test_vier_naechte_ohne_pauschalenfrage(self):
        # Kleingeschrieben suchen: im Text steht "Monteurpauschale"
        self.assertNotIn("pauschale", self._anfrage(4).lower())

    def test_acht_naechte_mit_pauschalenfrage(self):
        text = self._anfrage(8)
        self.assertIn("Monteurpauschale", text)
        self.assertIn("Bei 8 Nächten", text)

    def test_die_uebrigen_punkte_bleiben_in_beiden_faellen(self):
        for anzahl in (4, 8):
            text = self._anfrage(anzahl)
            self.assertIn("Frühstück serviert", text)
            self.assertIn("Parkmöglichkeit", text)
            self.assertIn("Stornierung", text)


class DoppelteKuerzel(unittest.TestCase):
    """Zwei gleiche Kürzel schicken sonst still den falschen Mann ins Hotel."""

    @staticmethod
    def _schreiben(tmp, inhalt):
        ordner = Path(tmp) / "hotels"
        ordner.mkdir(parents=True, exist_ok=True)
        (ordner / "monteure.yaml").write_text(inhalt, encoding="utf-8")
        os.environ["VORLAGENMANAGER_DATEN"] = tmp

    def tearDown(self):
        os.environ.pop("VORLAGENMANAGER_DATEN", None)

    def test_doppeltes_kuerzel_bricht_ab(self):
        from hotels import lade_monteure

        with tempfile.TemporaryDirectory() as tmp:
            self._schreiben(tmp, """
monteure:
  - kuerzel: IR
    name: Ivan Rusev
  - kuerzel: IR
    name: Ina Ruseva
""")
            with self.assertRaises(ValueError) as ctx:
                lade_monteure()
            meldung = str(ctx.exception)
            self.assertIn("Ivan Rusev", meldung)
            self.assertIn("Ina Ruseva", meldung)

    def test_gross_und_kleinschreibung_zaehlt_als_gleich(self):
        from hotels import lade_monteure

        with tempfile.TemporaryDirectory() as tmp:
            self._schreiben(tmp, """
monteure:
  - kuerzel: ir
    name: Ivan Rusev
  - kuerzel: IR
    name: Ina Ruseva
""")
            with self.assertRaises(ValueError):
                lade_monteure()

    def test_eindeutige_kuerzel_gehen_durch(self):
        from hotels import lade_monteure

        with tempfile.TemporaryDirectory() as tmp:
            self._schreiben(tmp, """
monteure:
  - kuerzel: IR
    name: Ivan Rusev
  - kuerzel: INR
    name: Ina Ruseva
""")
            self.assertEqual(len(lade_monteure()), 2)


class HeimfahrtGegenHotel(unittest.TestCase):
    """Bei Baustellen in Reichweite ist tägliches Heimfahren eine echte Option."""

    KRIT = {"dieselpreis_je_liter": 2.39, "durchschnittstempo_kmh": 40}

    def _rechnen(self, luftlinie, naechte, personen, preis, verbrauch=None):
        from hotels import heimfahrt_vergleich

        krit = dict(self.KRIT)
        if verbrauch:
            krit["verbrauch_je_100km"] = verbrauch
        return heimfahrt_vergleich(luftlinie, naechte, personen, preis, krit)

    def test_nahe_baustelle_spricht_fuer_heimfahrt(self):
        # Marburg, rund 89 km Strecke ab Fulda, 4 Nächte, 2 Mann
        v = self._rechnen(68, 4, 2, 86.50)
        self.assertGreater(v["ersparnis_heimfahrt"], 0)
        self.assertGreater(v["mehr_fahrstunden"], 0)

    def test_weite_baustelle_ist_nicht_zumutbar(self):
        # 400 km Luftlinie: Rein rechnerisch kann Heimfahren günstiger bleiben,
        # weil Sprit billiger ist als ein Zimmer. 13 Stunden Fahrt am Tag sind
        # aber keine Option, und genau das muss die Rechnung sagen.
        v = self._rechnen(400, 4, 2, 86.50)
        self.assertFalse(v["zumutbar"])
        self.assertGreater(v["fahrzeit_taeglich_h"], 3.0)

    def test_nahe_baustelle_ist_zumutbar(self):
        v = self._rechnen(68, 4, 2, 86.50)
        self.assertTrue(v["zumutbar"])
        self.assertLessEqual(v["fahrzeit_taeglich_h"], 3.0)

    def test_taegliche_fahrzeit_gilt_je_mann_nicht_als_summe(self):
        einer = self._rechnen(68, 4, 1, 90)
        zwei = self._rechnen(68, 4, 2, 90)
        self.assertEqual(einer["fahrzeit_taeglich_h"], zwei["fahrzeit_taeglich_h"])

    def test_arbeitstage_sind_naechte_plus_eins(self):
        self.assertEqual(self._rechnen(68, 4, 1, 90)["arbeitstage"], 5)
        self.assertEqual(self._rechnen(68, 1, 1, 90)["arbeitstage"], 2)

    def test_spesen_folgen_den_steuerlichen_pauschalen(self):
        # 4 Nächte, 1 Person: zwei Teiltage à 14 plus drei volle à 28
        v = self._rechnen(68, 4, 1, 90)
        self.assertAlmostEqual(v["hotel"]["spesen"], 2 * 14 + 3 * 28, places=2)
        # Heimfahrt: fünf Arbeitstage à 14
        self.assertAlmostEqual(v["heimfahrt"]["spesen"], 5 * 14, places=2)

    def test_hoeherer_verbrauch_kostet_mehr(self):
        sparsam = self._rechnen(68, 4, 2, 90, verbrauch=6.0)
        durstig = self._rechnen(68, 4, 2, 90, verbrauch=13.0)
        self.assertGreater(durstig["heimfahrt"]["sprit"], sparsam["heimfahrt"]["sprit"])

    def test_gefahrene_kilometer_sind_hin_und_zurueck(self):
        v = self._rechnen(100, 2, 1, 90)
        einfach = v["strecke_km"]
        self.assertAlmostEqual(v["hotel"]["km"], round(2 * einfach), delta=1)
        self.assertAlmostEqual(v["heimfahrt"]["km"], round(2 * einfach * 3), delta=2)

    def test_text_nennt_beide_richtungen(self):
        from hotels import vergleich_text

        nah = vergleich_text(self._rechnen(68, 4, 2, 86.50), 2)
        self.assertIn("Heimfahren spart", nah)
        fern = vergleich_text(self._rechnen(400, 4, 2, 86.50), 2)
        self.assertIn("scheidet aus", fern)


class PreisLeistungSichtbar(unittest.TestCase):
    def test_tabelle_zeigt_die_punkte(self):
        treffer = auswerten([hotel("Passt", 53.5400, 8.5810, 300)], BAUSTELLE,
                            zimmer=1, anzahl_naechte=4, kriterien=KRITERIEN)
        text = uebersicht(treffer)
        self.assertIn("P/L", text)
        self.assertIn("Preis-Leistungs-Verhältnis", text)


class EinsatzkostenStattNurZimmerpreis(unittest.TestCase):
    """Nähe kostet Zimmerpreis, Ferne kostet Sprit. Nur zusammen stimmt es.

    Der Fall aus Karlstadt: Platz 1 lag 13,9 km entfernt und kostete 95 EUR,
    Platz 3 lag 18,8 km entfernt und kostete 77 EUR. Die Rangfolge gewichtet
    Nähe und Preis getrennt und stellte deshalb das teurere Haus nach vorn,
    obwohl es über drei Nächte hundert Euro mehr kostet.
    """

    KRITERIEN = {"dieselpreis_je_liter": 2.39, "verbrauch_je_100km": 8.0}

    def _treffer(self, name, entfernung, preis):
        return Treffer(
            name=name,
            hotel_id=0,
            adresse="",
            plz="",
            ort="",
            bewertung=8.4,
            anzahl_bewertungen=100,
            sterne=3,
            gesamtpreis=preis * 6,
            preis_pro_nacht=preis,
            entfernung_km=entfernung,
            fahrzeit_min=fahrzeit_minuten(entfernung),
            park=beurteile_parkplatz(["Privatparkplatz"]),
            url="",
        )

    def test_der_naehere_ist_nicht_automatisch_der_guenstigere(self):
        nah = self._treffer("Nah und teuer", 13.9, 95.0)
        fern = self._treffer("Fern und billig", 18.8, 77.0)

        k_nah = einsatzkosten(nah, 2, 3, self.KRITERIEN)
        k_fern = einsatzkosten(fern, 2, 3, self.KRITERIEN)

        self.assertLess(k_fern["gesamt"], k_nah["gesamt"])
        # Der Zimmerunterschied ist 108 EUR, der Spritunterschied liegt weit
        # darunter. Genau das macht die getrennte Gewichtung unsichtbar.
        self.assertLess(k_fern["sprit"] - k_nah["sprit"], 20.0)

    def test_anfahrt_zaehlt_je_nacht_hin_und_zurueck(self):
        t = self._treffer("Zehn Kilometer", 10.0, 80.0)
        k = einsatzkosten(t, 1, 4, self.KRITERIEN)
        # 10 km Luftlinie, Umwegfaktor 1.3, zweimal je Nacht, vier Nächte.
        self.assertEqual(k["km"], round(2 * 13.0 * 4))

    def test_tabelle_nennt_den_guenstigeren_beim_namen(self):
        nah = self._treffer("Nah und teuer", 13.9, 95.0)
        fern = self._treffer("Fern und billig", 18.8, 77.0)
        text = kostentabelle([nah, fern], 2, 3, self.KRITERIEN)
        self.assertIn("Fern und billig", text)
        self.assertIn("günstiger als Platz 1", text)

    def test_ohne_hinweis_wenn_platz_eins_auch_unterm_strich_vorn_liegt(self):
        nah = self._treffer("Nah und billig", 5.0, 70.0)
        fern = self._treffer("Fern und teuer", 19.0, 99.0)
        text = kostentabelle([nah, fern], 2, 3, self.KRITERIEN)
        self.assertNotIn("günstiger als Platz 1", text)
