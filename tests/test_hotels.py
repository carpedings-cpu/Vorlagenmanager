"""Regressionstests für die Hotelsuche.

Abgesichert ist, was still falsch sein kann: eine Entfernung, die stimmt,
aber zum falschen Punkt gerechnet wird, ein Parkhaus, das als Stellplatz
durchgeht, ein Nachtpreis, der Zimmer und Nächte verwechselt. Ein Monteur
steht dann vor einem Hotel, in das sein Sprinter nicht passt.

    python3 -m unittest discover tests
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "werkzeuge"))

from hotels import (  # noqa: E402
    HOEHENGRENZE_PARKHAUS_M,
    auswerten,
    beurteile_parkplatz,
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
    """Der Punkt, an dem Booking nichts Brauchbares liefert."""

    def test_privatparkplatz_ist_in_ordnung(self):
        urteil = beurteile_parkplatz(["Privatparkplatz", "Parken vor Ort"])
        self.assertEqual(urteil.status, "ok")

    def test_reines_parkhaus_ist_fuer_den_sprinter_kritisch(self):
        urteil = beurteile_parkplatz(["Parkplatz", "Parkhaus"], fahrzeughoehe_m=2.60)
        self.assertEqual(urteil.status, "kritisch")
        self.assertIn("2.60", urteil.hinweis)

    def test_parkhaus_bei_flachem_fahrzeug_nur_pruefen(self):
        urteil = beurteile_parkplatz(
            ["Parkplatz", "Parkhaus"], fahrzeughoehe_m=HOEHENGRENZE_PARKHAUS_M
        )
        self.assertEqual(urteil.status, "pruefen")

    def test_strassenparken_ist_kein_stellplatz(self):
        urteil = beurteile_parkplatz(["Parkplätze an der Straße"])
        self.assertEqual(urteil.status, "kritisch")

    def test_ohne_angabe_kein_parkplatz(self):
        self.assertEqual(beurteile_parkplatz([]).status, "kritisch")

    def test_unklare_angabe_wird_zum_nachfragen(self):
        self.assertEqual(beurteile_parkplatz(["Parkplatz"]).status, "pruefen")

    def test_stellplatz_und_parkhaus_bleibt_zu_pruefen(self):
        urteil = beurteile_parkplatz(["Privatparkplatz", "Parkhaus"])
        self.assertEqual(urteil.status, "pruefen")


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

    def test_parkhaus_fliegt_beim_sprinter_raus(self):
        treffer = auswerten(
            [hotel("Nur Parkhaus", 53.5400, 8.5810, 300, ausstattung=["Parkhaus"])],
            BAUSTELLE,
            zimmer=1,
            anzahl_naechte=4,
            kriterien=KRITERIEN,
            fahrzeughoehe_m=2.60,
        )
        self.assertFalse(treffer[0].geeignet)
        self.assertIn("Parken", treffer[0].ausschluss)

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
        {"kuerzel": "MK", "name": "Max Mustermann", "fahrzeughoehe_m": 2.60},
        {"kuerzel": "TS", "name": "Thomas Schmitt", "fahrzeughoehe_m": 1.95},
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
    """Kein Bewertungsfeld heißt unbewertet, nicht mit 0,0 bewertet."""

    @staticmethod
    def _ohne_bewertung():
        roh = hotel("Neu eröffnet", 53.5400, 8.5810, 300)
        roh["rating"] = {}
        return roh

    def test_grund_nennt_die_fehlende_bewertung(self):
        treffer = auswerten([self._ohne_bewertung()], BAUSTELLE, zimmer=1,
                            anzahl_naechte=4, kriterien=KRITERIEN)
        self.assertIn("keine Bewertung", treffer[0].ausschluss)
        self.assertNotIn("0.0", treffer[0].ausschluss)

    def test_kein_doppelter_grund_fuer_dieselbe_luecke(self):
        treffer = auswerten([self._ohne_bewertung()], BAUSTELLE, zimmer=1,
                            anzahl_naechte=4, kriterien=KRITERIEN)
        self.assertEqual(treffer[0].ausschluss.count(";"), 0)

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


class HoeheWirdNichtBehauptet(unittest.TestCase):
    """Praxisfall Limehome Berlin: grüner Stellplatz, trotzdem 2,00 m Schranke."""

    def test_stellplatz_ohne_parkhaus_behauptet_keine_hoehe(self):
        urteil = beurteile_parkplatz(["Privatparkplatz", "Parken vor Ort"])
        self.assertEqual(urteil.status, "ok")
        self.assertIn("unbestätigt", urteil.hinweis)
        self.assertNotIn("ebenerdig", urteil.hinweis)

    def test_uebersicht_fordert_die_hoehe_immer_an(self):
        treffer = auswerten([hotel("Passt", 53.5400, 8.5810, 300)], BAUSTELLE,
                            zimmer=1, anzahl_naechte=4, kriterien=KRITERIEN)
        self.assertIn("Durchfahrtshöhe", uebersicht(treffer))


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


class BekannteHoehen(unittest.TestCase):
    """Einmal erfragt, gilt weiter. Ein Parkhaus wird nicht höher."""

    @staticmethod
    def _haus(hid=77):
        # Ausstattung sagt "eigener Stellplatz", die erfragte Höhe sagt etwas anderes
        return hotel("Sieht gut aus", 53.5400, 8.5810, 300,
                     ausstattung=["Privatparkplatz", "Parken vor Ort"], hid=hid)

    def test_erfragte_hoehe_schlaegt_die_ausstattungsliste(self):
        hoehen = {77: {"meter": 2.00, "geprueft_am": "16.09.2026"}}
        treffer = auswerten([self._haus()], BAUSTELLE, zimmer=1, anzahl_naechte=4,
                            kriterien=KRITERIEN, fahrzeughoehe_m=2.35, hoehen=hoehen)
        self.assertFalse(treffer[0].geeignet)
        self.assertIn("2.00 m", treffer[0].ausschluss)

    def test_ausschlussgrund_nennt_das_pruefdatum(self):
        hoehen = {77: {"meter": 1.80, "geprueft_am": "16.09.2026"}}
        treffer = auswerten([self._haus()], BAUSTELLE, zimmer=1, anzahl_naechte=4,
                            kriterien=KRITERIEN, fahrzeughoehe_m=2.35, hoehen=hoehen)
        self.assertIn("16.09.2026", treffer[0].ausschluss)

    def test_ausreichende_hoehe_laesst_das_haus_durch(self):
        hoehen = {77: {"meter": 3.20, "geprueft_am": "16.09.2026"}}
        treffer = auswerten([self._haus()], BAUSTELLE, zimmer=1, anzahl_naechte=4,
                            kriterien=KRITERIEN, fahrzeughoehe_m=2.35, hoehen=hoehen)
        self.assertTrue(treffer[0].geeignet, treffer[0].ausschluss)
        self.assertIn("3.20 m", treffer[0].park.hinweis)

    def test_ohne_eintrag_bleibt_es_bei_der_ableitung(self):
        treffer = auswerten([self._haus()], BAUSTELLE, zimmer=1, anzahl_naechte=4,
                            kriterien=KRITERIEN, fahrzeughoehe_m=2.35, hoehen={})
        self.assertIn("unbestätigt", treffer[0].park.hinweis)

    def test_eintrag_gilt_nur_fuer_das_eigene_haus(self):
        hoehen = {999: {"meter": 1.80, "geprueft_am": "16.09.2026"}}
        treffer = auswerten([self._haus(hid=77)], BAUSTELLE, zimmer=1,
                            anzahl_naechte=4, kriterien=KRITERIEN,
                            fahrzeughoehe_m=2.35, hoehen=hoehen)
        self.assertTrue(treffer[0].geeignet)

    def test_flaches_fahrzeug_kommt_durch_dieselbe_einfahrt(self):
        hoehen = {77: {"meter": 2.00, "geprueft_am": "16.09.2026"}}
        treffer = auswerten([self._haus()], BAUSTELLE, zimmer=1, anzahl_naechte=4,
                            kriterien=KRITERIEN, fahrzeughoehe_m=1.95, hoehen=hoehen)
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
            "fahrzeughoehe": "2,35",
            "fruehstueck_ab": "06:00",
            "pauschale": "ja" if naechte_zahl >= 5 else "",
            "hinweis": "",
            "absender": "Diana Ziegler",
            "firma": "KPC GmbH",
        }
        vorlage = repowurzel() / "vorlagen" / "hotelanfrage" / "anfrage.md"
        return ersetze_in_markdown(vorlage.read_text(encoding="utf-8"), werte)

    def test_vier_naechte_ohne_pauschalenfrage(self):
        self.assertNotIn("Pauschale", self._anfrage(4))

    def test_acht_naechte_mit_pauschalenfrage(self):
        text = self._anfrage(8)
        self.assertIn("Pauschale", text)
        self.assertIn("Bei 8 Nächten", text)

    def test_die_uebrigen_punkte_bleiben_in_beiden_faellen(self):
        for anzahl in (4, 8):
            text = self._anfrage(anzahl)
            self.assertIn("Frühstück serviert", text)
            self.assertIn("Durchfahrt", text)
            self.assertIn("Stornierung", text)
