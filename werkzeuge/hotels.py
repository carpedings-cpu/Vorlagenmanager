"""Bausteine für die Monteur-Hotelsuche.

Die Live-Suche selbst läuft nicht hier, sondern über den Booking-Zugang von
Claude. Dieses Modul macht das Drumherum, das eine Portalsuche nicht kann:

* Baustellen und Monteure aus den Stammdaten holen
* Entfernung Hotel–Baustelle rechnen
* aus der Ausstattungsliste ableiten, ob ein eigener Stellplatz da ist
* die Treffer nach festen Kriterien filtern und in eine Rangfolge bringen

Programm und Daten sind getrennt wie im übrigen Vorlagenmanager: Die
Stammdaten liegen im Datenordner unter `hotels/`, nicht im Repo. Monteurnamen
sind Personendaten und haben in einem Git-Repository nichts verloren.
"""

from __future__ import annotations

import math
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

import yaml

from kern import datenwurzel, lade_yaml, repowurzel

DATUMSFORMAT = "%d.%m.%Y"
ISOFORMAT = "%Y-%m-%d"

# Umweg über die Straße gegenüber der Luftlinie. Grober Erfahrungswert für
# deutsche Mittelstädte; er ersetzt keine Routenberechnung und wird in der
# Ausgabe auch als Schätzung gekennzeichnet.
UMWEGFAKTOR = 1.3
DURCHSCHNITTSTEMPO_KMH = 40.0

# Ob der Parkplatz für das jeweilige Fahrzeug hoch genug ist, prüft Diana
# selbst beim Haus. Hier zählt nur, ob es überhaupt einen gibt.


# --- Stammdaten ------------------------------------------------------------


def hotelordner() -> Path:
    """Ordner mit baustellen.yaml, monteure.yaml, kriterien.yaml, buchungen.yaml."""
    return datenwurzel() / "hotels"


def _lade_stammdatei(name: str, schluessel: str) -> list[dict]:
    pfad = hotelordner() / name
    if not pfad.exists():
        raise FileNotFoundError(
            f"{pfad} fehlt.\n"
            "Anlegen: python3 werkzeuge/einrichten.py <Datenordner>, dann die "
            f"Vorlage in stammdaten/_vorlage_{name} ausfüllen."
        )
    daten = lade_yaml(pfad)
    return daten.get(schluessel, []) or []


def lade_baustellen() -> list[dict]:
    return _lade_stammdatei("baustellen.yaml", "baustellen")


def lade_monteure() -> list[dict]:
    monteure = _lade_stammdatei("monteure.yaml", "monteure")
    _pruefe_kuerzel(monteure)
    return monteure


def _pruefe_kuerzel(leute: list[dict]) -> None:
    """Bricht ab, wenn zwei Personen dasselbe Kürzel tragen.

    Sonst gewinnt beim Nachschlagen still die letzte, und im Hotel liegt der
    falsche Mann. Zwei Nachnamen mit gleichem Anfangsbuchstaben reichen dafür
    schon: Ivan Rusev und Ina Ruseva ergeben beide IR.
    """
    gesehen: dict[str, str] = {}
    doppelt: list[str] = []
    for person in leute:
        schluessel = _normalisiere(person.get("kuerzel", ""))
        if not schluessel:
            continue
        name = person.get("name") or person.get("kuerzel", "?")
        if schluessel in gesehen:
            doppelt.append(
                f"{person.get('kuerzel')} für {gesehen[schluessel]} und {name}"
            )
        else:
            gesehen[schluessel] = name
    if doppelt:
        raise ValueError(
            "Kürzel doppelt vergeben: "
            + "; ".join(doppelt)
            + ". In monteure.yaml eindeutig machen."
        )


def lade_kriterien() -> dict:
    """Suchkriterien: erst die Vorgabe aus dem Repo, dann eigene Werte darüber."""
    grund = lade_yaml(repowurzel() / "stammdaten" / "kriterien.yaml")
    eigen_pfad = hotelordner() / "kriterien.yaml"
    if eigen_pfad.exists():
        grund.update(lade_yaml(eigen_pfad))
    return grund


def _normalisiere(text: str) -> str:
    """Kleinschreibung ohne Umlaute und Sonderzeichen, für den Namensvergleich."""
    zerlegt = unicodedata.normalize("NFKD", str(text).lower())
    ohne_akzente = "".join(z for z in zerlegt if not unicodedata.combining(z))
    ersetzungen = {"ß": "ss", "ä": "ae", "ö": "oe", "ü": "ue"}
    for alt, neu in ersetzungen.items():
        ohne_akzente = ohne_akzente.replace(alt, neu)
    return "".join(z for z in ohne_akzente if z.isalnum())


def finde_baustelle(suchbegriff: str, baustellen: list[dict] | None = None) -> dict:
    """Findet eine Baustelle über Kürzel, Projektnummer, Kurzname oder Ort.

    Bleibt es mehrdeutig, wird das gemeldet statt geraten – eine Suche am
    falschen Ort fällt erst auf, wenn der Monteur 200 km weiter steht.
    """
    baustellen = baustellen if baustellen is not None else lade_baustellen()
    gesucht = _normalisiere(suchbegriff)

    genau = [
        b
        for b in baustellen
        if gesucht
        in {
            _normalisiere(b.get("kuerzel", "")),
            _normalisiere(b.get("projektnummer", "")),
            _normalisiere(b.get("kurzname", "")),
        }
    ]
    if len(genau) == 1:
        return genau[0]

    teilweise = [
        b
        for b in baustellen
        if gesucht
        and gesucht
        in _normalisiere(
            f"{b.get('kurzname', '')}{b.get('ort', '')}{b.get('projektnummer', '')}"
        )
    ]
    treffer = genau or teilweise

    if not treffer:
        namen = ", ".join(b.get("kurzname", "?") for b in baustellen) or "keine"
        raise LookupError(f"Keine Baustelle zu '{suchbegriff}'. Hinterlegt: {namen}")
    if len(treffer) > 1:
        namen = ", ".join(b.get("kurzname", "?") for b in treffer)
        raise LookupError(f"'{suchbegriff}' passt auf mehrere Baustellen: {namen}")
    return treffer[0]


def finde_monteure(kuerzel: list[str], alle: list[dict] | None = None) -> list[dict]:
    alle = alle if alle is not None else lade_monteure()
    nach_kuerzel = {_normalisiere(m.get("kuerzel", "")): m for m in alle}
    nach_name = {_normalisiere(m.get("name", "")): m for m in alle}

    gefunden = []
    unbekannt = []
    for eintrag in kuerzel:
        schluessel = _normalisiere(eintrag)
        person = nach_kuerzel.get(schluessel) or nach_name.get(schluessel)
        if person is None:
            person = next(
                (m for k, m in nach_name.items() if schluessel and schluessel in k),
                None,
            )
        if person is None:
            unbekannt.append(eintrag)
        else:
            gefunden.append(person)

    if unbekannt:
        bekannt = ", ".join(m.get("kuerzel", "?") for m in alle) or "keine"
        raise LookupError(
            f"Unbekannt: {', '.join(unbekannt)}. Hinterlegt: {bekannt}"
        )
    return gefunden


# --- Entfernung ------------------------------------------------------------


def luftlinie_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Entfernung auf der Kugel, Erdradius 6371 km."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return 6371.0 * 2 * math.asin(math.sqrt(a))


def fahrstrecke_km(luftlinie: float) -> float:
    return luftlinie * UMWEGFAKTOR


def fahrzeit_minuten(luftlinie: float) -> int:
    return round(fahrstrecke_km(luftlinie) / DURCHSCHNITTSTEMPO_KMH * 60)


# --- Parkplatz -------------------------------------------------------------

# Was in der Ausstattungsliste für einen eigenen Stellplatz spricht und was
# dagegen. Ob das Fahrzeug dort auch hineinpasst, klärt sich beim Haus.
PARKEN_EIGEN = (
    "privatparkplatz",
    "parken vor ort",
    "parkplatz inbegriffen",
    "kostenlose parkplätze",
    "kostenloser parkplatz",
    "überdachte parkplätze",
    "parkhaus",
    "tiefgarage",
    "garage",
)
PARKEN_NUR_STRASSE = ("parkplätze an der straße", "öffentliche parkplätze")
PARKEN_ALLGEMEIN = ("parkplatz", "parken")


@dataclass
class Parkurteil:
    status: str  # "ok", "pruefen", "kritisch"
    hinweis: str

    @property
    def zeichen(self) -> str:
        return {"ok": "✅", "pruefen": "🔍", "kritisch": "⛔"}[self.status]


def beurteile_parkplatz(ausstattung: list[str]) -> Parkurteil:
    """Sagt, ob das Haus einen eigenen Stellplatz hat.

    Mehr gibt die Ausstattungsliste nicht her. Ob das Fahrzeug dort auch
    hineinpasst, klärt sich beim Haus und nicht in einer Datenbank.
    """
    klein = [str(a).lower() for a in ausstattung]

    def enthaelt(begriffe: tuple[str, ...]) -> bool:
        return any(b in eintrag for eintrag in klein for b in begriffe)

    if enthaelt(PARKEN_EIGEN):
        return Parkurteil("ok", "eigener Stellplatz")
    if enthaelt(PARKEN_NUR_STRASSE):
        return Parkurteil("kritisch", "nur Parken am Straßenrand")
    if enthaelt(PARKEN_ALLGEMEIN):
        return Parkurteil("pruefen", "Parkplatz genannt, Art unklar")
    return Parkurteil("kritisch", "kein Parkplatz angegeben")


# --- Treffer bewerten ------------------------------------------------------


@dataclass
class Treffer:
    name: str
    hotel_id: int
    adresse: str
    plz: str
    ort: str
    bewertung: float
    anzahl_bewertungen: int
    sterne: int
    gesamtpreis: float
    preis_pro_nacht: float
    entfernung_km: float
    fahrzeit_min: int
    park: Parkurteil
    url: str
    ausschluss: str = ""
    hat_bewertung: bool = True
    punkte: float = 0.0
    ausstattung: list[str] = field(default_factory=list)

    @property
    def geeignet(self) -> bool:
        return not self.ausschluss


def _zahl(wert, ersatz: float = 0.0) -> float:
    try:
        return float(wert)
    except (TypeError, ValueError):
        return ersatz


def naechte(von: str, bis: str) -> int:
    """Anzahl Übernachtungen zwischen zwei Datumsangaben (TT.MM.JJJJ oder ISO)."""
    return (_als_datum(bis) - _als_datum(von)).days


def _als_datum(wert: str | date) -> date:
    if isinstance(wert, date):
        return wert
    text = str(wert).strip()
    for muster in (DATUMSFORMAT, ISOFORMAT):
        try:
            return datetime.strptime(text, muster).date()
        except ValueError:
            continue
    raise ValueError(f"Datum nicht verstanden: {wert!r} (erwartet TT.MM.JJJJ)")


def als_iso(wert: str | date) -> str:
    return _als_datum(wert).strftime(ISOFORMAT)


def als_deutsch(wert: str | date) -> str:
    return _als_datum(wert).strftime(DATUMSFORMAT)


def auswerten(
    rohtreffer: list[dict],
    baustelle: dict,
    zimmer: int,
    anzahl_naechte: int,
    kriterien: dict | None = None,
) -> list[Treffer]:
    """Rechnet Entfernung und Nachtpreis, prüft die Kriterien, sortiert.

    Ausgeschlossene Treffer fliegen nicht raus, sondern bekommen einen Grund.
    Wenn im Umkreis nichts Passendes frei ist, will man sehen, woran es lag.
    """
    kriterien = kriterien or lade_kriterien()
    koord = baustelle.get("koordinaten") or {}
    b_lat, b_lon = _zahl(koord.get("lat")), _zahl(koord.get("lon"))
    if not b_lat or not b_lon:
        raise ValueError(
            f"Baustelle '{baustelle.get('kurzname', '?')}' hat keine Koordinaten. "
            "In baustellen.yaml unter koordinaten: lat/lon eintragen."
        )

    max_entfernung = _zahl(
        baustelle.get("max_entfernung_km") or kriterien.get("max_entfernung_km"), 25.0
    )
    min_bewertung = _zahl(kriterien.get("mindestbewertung"), 8.0)
    # In Berlin bleibt bei 120 EUR fast nichts übrig, in Marburg ist der Wert
    # großzügig. Deshalb darf die Baustelle ihn überschreiben, wie den Radius.
    max_nacht = _zahl(
        baustelle.get("max_preis_pro_nacht")
        if baustelle.get("max_preis_pro_nacht") is not None
        else kriterien.get("max_preis_pro_nacht"),
        0.0,
    )
    min_anzahl = int(_zahl(kriterien.get("mindestanzahl_bewertungen"), 0))
    parken_pflicht = bool(kriterien.get("parkplatz_pflicht", True))

    zimmer = max(1, int(zimmer))
    anzahl_naechte = max(1, int(anzahl_naechte))

    ergebnis: list[Treffer] = []
    for roh in rohtreffer:
        ort_daten = roh.get("location") or {}
        h_koord = ort_daten.get("coordinates") or {}
        bewertung_daten = roh.get("rating") or {}
        preis_daten = roh.get("price") or {}
        ausstattung = roh.get("facilities") or []

        entfernung = luftlinie_km(
            b_lat, b_lon, _zahl(h_koord.get("latitude")), _zahl(h_koord.get("longitude"))
        )
        gesamt = _zahl(preis_daten.get("book"))
        pro_nacht = gesamt / zimmer / anzahl_naechte if gesamt else 0.0
        # Fehlt das Bewertungsfeld ganz, ist das Hotel nicht schlecht bewertet,
        # sondern unbewertet. Der Unterschied gehört in den Ausschlussgrund.
        hat_bewertung = bewertung_daten.get("review_score") is not None
        bewertung = _zahl(bewertung_daten.get("review_score"))
        anzahl_bew = int(_zahl(bewertung_daten.get("number_of_reviews")))
        hotel_id = int(_zahl(roh.get("id")))
        park = beurteile_parkplatz(ausstattung)

        gruende = []
        if entfernung > max_entfernung:
            gruende.append(f"{entfernung:.1f} km, mehr als {max_entfernung:.0f} km")
        # Ein Haus ohne Bewertung ist nicht schlecht bewertet, es ist unbekannt.
        # Es fliegt deshalb nicht raus, sondern steht mit Hinweis in der Liste
        # und verliert nur die Punkte, die es nicht belegen kann. Sonst fällt
        # ein neues Haus, das näher und billiger liegt als alle bewerteten,
        # still unter den Tisch - genau das ist in Karlstadt passiert.
        if not hat_bewertung:
            pass
        elif bewertung < min_bewertung:
            gruende.append(f"Bewertung {bewertung:.1f} unter {min_bewertung:.1f}")
        elif min_anzahl and anzahl_bew < min_anzahl:
            gruende.append(f"nur {anzahl_bew} Bewertungen")
        if max_nacht and pro_nacht > max_nacht:
            gruende.append(f"{pro_nacht:.0f} EUR/Nacht über Limit {max_nacht:.0f} EUR")
        if parken_pflicht and park.status == "kritisch":
            gruende.append(f"Parken: {park.hinweis}")

        ergebnis.append(
            Treffer(
                name=roh.get("name", "?"),
                hotel_id=hotel_id,
                adresse=ort_daten.get("address", ""),
                plz=str(ort_daten.get("postal_code", "")),
                ort=ort_daten.get("city_name", ""),
                bewertung=bewertung,
                anzahl_bewertungen=anzahl_bew,
                sterne=int(_zahl(bewertung_daten.get("stars"))),
                gesamtpreis=gesamt,
                preis_pro_nacht=pro_nacht,
                entfernung_km=entfernung,
                fahrzeit_min=fahrzeit_minuten(entfernung),
                park=park,
                url=roh.get("url", ""),
                ausschluss="; ".join(gruende),
                hat_bewertung=hat_bewertung,
                ausstattung=list(ausstattung),
            )
        )

    _punkte_vergeben(ergebnis, kriterien, max_entfernung, max_nacht)
    ergebnis.sort(key=lambda t: (not t.geeignet, -t.punkte))
    return ergebnis


def _punkte_vergeben(
    treffer: list[Treffer],
    kriterien: dict,
    max_entfernung: float,
    max_nacht: float = 0.0,
) -> None:
    """Punktet Entfernung, Preis, Bewertung und Parkplatz auf einer 0..100-Skala.

    Bewusst nachvollziehbar gehalten: Jeder Anteil ist einzeln erklärbar,
    damit man einer Rangfolge ansieht, warum sie so ist.
    """
    geeignete = [t for t in treffer if t.geeignet]
    if not geeignete:
        return

    gewicht_entfernung = _zahl(kriterien.get("gewicht_entfernung"), 40.0)
    gewicht_preis = _zahl(kriterien.get("gewicht_preis"), 30.0)
    gewicht_bewertung = _zahl(kriterien.get("gewicht_bewertung"), 20.0)
    gewicht_parken = _zahl(kriterien.get("gewicht_parken"), 10.0)

    preise = [t.preis_pro_nacht for t in geeignete if t.preis_pro_nacht > 0]
    teuerst = max(preise) if preise else 0.0

    # Bezugsgröße ist das Preislimit, nicht die Spanne der Treffer. Sonst wird
    # aus vier Euro Unterschied zwischen zwei Hotels die volle Punktzahl, und
    # ein Haus acht Kilometer weiter draußen gewinnt wegen fast nichts.
    bezug = max_nacht or _zahl(kriterien.get("max_preis_pro_nacht"), 0.0) or teuerst

    for t in treffer:
        nah = 1 - min(t.entfernung_km / max_entfernung, 1.0) if max_entfernung else 0.0
        if bezug > 0 and t.preis_pro_nacht > 0:
            guenstig = max(0.0, 1 - t.preis_pro_nacht / bezug)
        else:
            guenstig = 1.0
        if t.hat_bewertung:
            gut = max(0.0, min((t.bewertung - 7.0) / 3.0, 1.0))
        else:
            # Weder Gutes noch Schlechtes bekannt: die Hälfte der Punkte. Volle
            # Punkte wären geschönt, keine wären eine Strafe für Neueröffnung.
            gut = 0.5
        parken = {"ok": 1.0, "pruefen": 0.5, "kritisch": 0.0}[t.park.status]

        t.punkte = round(
            nah * gewicht_entfernung
            + guenstig * gewicht_preis
            + gut * gewicht_bewertung
            + parken * gewicht_parken,
            1,
        )


# --- Ausgabe ---------------------------------------------------------------


def uebersicht(treffer: list[Treffer], anzahl: int = 5) -> str:
    """Markdown-Tabelle der geeigneten Treffer, darunter die Aussortierten."""
    geeignete = [t for t in treffer if t.geeignet][:anzahl]
    if not geeignete:
        return _keine_treffer(treffer)

    zeilen = [
        "| # | Hotel | Entfernung | EUR/Nacht | Bewertung | P/L | Parkplatz |",
        "|---|---|---|---|---|---|---|",
    ]
    for nr, t in enumerate(geeignete, 1):
        zeilen.append(
            f"| {nr} | [{t.name}]({t.url}) | {t.entfernung_km:.1f} km "
            f"(ca. {t.fahrzeit_min} min) | {t.preis_pro_nacht:.2f} | "
            + (f"{t.bewertung:.1f} ({t.anzahl_bewertungen})" if t.hat_bewertung
               else "ohne Bewertung")
            + f" | {t.punkte:.0f} | "
            f"{t.park.zeichen} {t.park.hinweis} |"
        )

    aussortiert = [t for t in treffer if not t.geeignet]
    if aussortiert:
        zeilen.append("")
        zeilen.append("Aussortiert:")
        for t in aussortiert[:8]:
            zeilen.append(f"- {t.name}: {t.ausschluss}")

    zeilen.append("")
    zeilen.append(
        "Entfernung ist Luftlinie, die Fahrzeit eine Schätzung "
        f"(Faktor {UMWEGFAKTOR} auf die Strecke, {DURCHSCHNITTSTEMPO_KMH:.0f} km/h)."
    )
    zeilen.append(
        "P/L ist das Preis-Leistungs-Verhältnis von 0 bis 100, gewichtet aus "
        "Nähe zur Baustelle, Preis, Bewertung und Parkplatz. Platz 1 hat davon "
        "das beste."
    )
    if any(not t.hat_bewertung for t in geeignete):
        zeilen.append(
            "Häuser ohne Bewertung sind nicht schlecht bewertet, sondern noch "
            "unbewertet, oft neu eröffnet. Sie zählen bei der Bewertung mit der "
            "halben Punktzahl und sind vor dem Buchen einen Blick auf die Fotos "
            "wert."
        )
    return "\n".join(zeilen)


def _keine_treffer(treffer: list[Treffer]) -> str:
    if not treffer:
        return "Keine Treffer. Radius vergrößern oder Zeitraum prüfen."
    zeilen = ["Kein Hotel erfüllt alle Kriterien. Woran es lag:", ""]
    for t in treffer[:10]:
        zeilen.append(f"- {t.name}: {t.ausschluss}")
    zeilen.append("")
    zeilen.append(
        "Lockern lässt sich in kriterien.yaml: max_entfernung_km, "
        "mindestbewertung oder max_preis_pro_nacht."
    )
    return "\n".join(zeilen)


def kostenschaetzung(treffer: Treffer, zimmer: int, anzahl_naechte: int) -> str:
    gesamt = treffer.preis_pro_nacht * zimmer * anzahl_naechte
    return (
        f"{zimmer} Zimmer × {anzahl_naechte} Nächte × "
        f"{treffer.preis_pro_nacht:.2f} EUR = {gesamt:.2f} EUR"
    )


def einsatzkosten(
    treffer: Treffer,
    zimmer: int,
    anzahl_naechte: int,
    kriterien: dict | None = None,
) -> dict:
    """Zimmer plus Diesel für die täglichen Wege zwischen Hotel und Baustelle.

    Ohne diesen zweiten Posten vergleicht man Äpfel mit Birnen: Ein Haus fünf
    Kilometer weiter draußen kostet über eine Woche keine zwanzig Euro mehr
    Sprit, kann beim Zimmerpreis aber hundert Euro billiger sein. Die
    Rangfolge gewichtet Nähe und Preis getrennt und sieht das nicht.
    """
    kriterien = kriterien or lade_kriterien()
    dieselpreis = _zahl(kriterien.get("dieselpreis_je_liter"), 2.39)
    liter100 = _zahl(kriterien.get("verbrauch_je_100km"), VERBRAUCH_JE_100KM)

    zimmerkosten = treffer.preis_pro_nacht * zimmer * anzahl_naechte
    # Je Nacht einmal hin und einmal zurück, mit einem Fahrzeug gerechnet wie
    # beim Heimfahrtvergleich.
    km = 2 * fahrstrecke_km(treffer.entfernung_km) * anzahl_naechte
    sprit = km / 100 * liter100 * dieselpreis

    return {
        "zimmer": round(zimmerkosten, 2),
        "sprit": round(sprit, 2),
        "km": round(km),
        "gesamt": round(zimmerkosten + sprit, 2),
    }


def kostentabelle(
    treffer: list[Treffer],
    zimmer: int,
    anzahl_naechte: int,
    kriterien: dict | None = None,
) -> str:
    """Stellt die Vorschläge mit Zimmer, Anfahrt und Summe nebeneinander."""
    kriterien = kriterien or lade_kriterien()
    posten = [
        (t, einsatzkosten(t, zimmer, anzahl_naechte, kriterien)) for t in treffer
    ]
    if not posten:
        return ""

    zeilen = [
        "| Hotel | Zimmer | Anfahrt | Summe |",
        "|---|---|---|---|",
    ]
    for t, k in posten:
        zeilen.append(
            f"| {t.name} | {k['zimmer']:.2f} EUR | "
            f"{k['sprit']:.2f} EUR ({k['km']} km) | **{k['gesamt']:.2f} EUR** |"
        )

    guenstigst = min(posten, key=lambda p: p[1]["gesamt"])
    if guenstigst[0] is not posten[0][0]:
        unterschied = posten[0][1]["gesamt"] - guenstigst[1]["gesamt"]
        zeilen.append("")
        zeilen.append(
            f"Unterm Strich ist {guenstigst[0].name} {unterschied:.2f} EUR "
            f"günstiger als Platz 1, trotz der längeren Anfahrt."
        )
    zeilen.append("")
    zeilen.append(
        f"Zimmer für {zimmer} × {anzahl_naechte} Nächte, Anfahrt je Nacht einmal "
        "hin und zurück mit einem Fahrzeug."
    )
    return "\n".join(zeilen)


# --- Buchungen festhalten --------------------------------------------------


# --- Heimfahrt statt Hotel -------------------------------------------------

# Verbrauch in Litern je 100 km. Richtwerte für Dieselfahrzeuge im
# Montageeinsatz, also beladen und nicht auf Verbrauch gefahren.
# Durchschnittsverbrauch für die Heimfahrtrechnung, alle Fahrzeuge Diesel.
# Anpassbar in kriterien.yaml unter verbrauch_je_100km.
VERBRAUCH_JE_100KM = 8.0

# Verpflegungsmehraufwand im Inland, steuerfreie Pauschalen.
SPESEN_VOLLER_TAG = 28.0
SPESEN_TEILTAG = 14.0

# Ab wann tägliches Heimfahren keine Option mehr ist. Reiner Kostenvergleich
# sagt "fahr heim" auch bei 500 km, weil ein Hotelzimmer teurer ist als der
# Sprit. Bei acht Stunden Montage passen aber nur zwei Stunden Fahrt in den
# Zehn-Stunden-Rahmen des Arbeitszeitgesetzes.
FAHRZEIT_ZUMUTBAR_H = 3.0

# Die 40 km/h weiter oben gelten für den kurzen Weg vom Hotel zur Baustelle,
# also Ortsdurchfahrten und Ampeln. Die Heimfahrt über hundert Kilometer läuft
# überwiegend über Land und Autobahn.
FERNTEMPO_KMH = 75.0


def heimfahrt_vergleich(
    entfernung_km: float,
    anzahl_naechte: int,
    personen: int,
    preis_pro_nacht: float,
    kriterien: dict | None = None,
    fahrzeuge: int = 1,
) -> dict:
    """Stellt Hotelaufenthalt und tägliche Heimfahrt gegenüber.

    Gerechnet wird mit Strecke, nicht mit Luftlinie, und beide Seiten tragen
    dieselben Posten: Kraftstoff, Verpflegungspauschale, Fahrzeit. Die Fahrzeit
    wird nur ausgewiesen, nicht bewertet - ob sie als Arbeitszeit zählt, ist
    eine betriebliche Frage und keine Rechenregel.
    """
    kriterien = kriterien or lade_kriterien()
    dieselpreis = _zahl(kriterien.get("dieselpreis_je_liter"), 2.39)
    tempo = _zahl(kriterien.get("ferntempo_kmh"), FERNTEMPO_KMH)

    strecke = fahrstrecke_km(entfernung_km)
    liter100 = _zahl(kriterien.get("verbrauch_je_100km"), VERBRAUCH_JE_100KM)
    arbeitstage = max(1, anzahl_naechte + 1)

    # Hotel: einmal hin, einmal zurück.
    hotel_km = 2 * strecke * fahrzeuge
    hotel_sprit = hotel_km / 100 * liter100 * dieselpreis
    hotel_zimmer = preis_pro_nacht * personen * anzahl_naechte
    # Erster und letzter Tag zählen als Teiltag, die Tage dazwischen voll.
    hotel_spesen = personen * (
        2 * SPESEN_TEILTAG + max(0, anzahl_naechte - 1) * SPESEN_VOLLER_TAG
    )
    hotel_fahrstunden = 2 * strecke / tempo * fahrzeuge

    # Heimfahrt: jeden Arbeitstag hin und zurück, keine Übernachtung.
    heim_km = 2 * strecke * arbeitstage * fahrzeuge
    heim_sprit = heim_km / 100 * liter100 * dieselpreis
    heim_spesen = personen * arbeitstage * SPESEN_TEILTAG
    heim_fahrstunden = 2 * strecke / tempo * arbeitstage * fahrzeuge

    hotel_gesamt = hotel_zimmer + hotel_sprit + hotel_spesen
    heim_gesamt = heim_sprit + heim_spesen

    # Was ein einzelner Mann täglich fährt, nicht die Summe aller Fahrzeuge.
    fahrzeit_taeglich = 2 * strecke / tempo
    zumutbar = _zahl(
        kriterien.get("fahrzeit_zumutbar_h"), FAHRZEIT_ZUMUTBAR_H
    )

    return {
        "strecke_km": round(strecke, 1),
        "arbeitstage": arbeitstage,
        "fahrzeit_taeglich_h": round(fahrzeit_taeglich, 1),
        "zumutbar": fahrzeit_taeglich <= zumutbar,
        "zumutbar_grenze_h": zumutbar,
        "tempo_kmh": tempo,
        "dieselpreis": dieselpreis,
        "verbrauch": liter100,
        "hotel": {
            "zimmer": round(hotel_zimmer, 2),
            "sprit": round(hotel_sprit, 2),
            "spesen": round(hotel_spesen, 2),
            "gesamt": round(hotel_gesamt, 2),
            "fahrstunden": round(hotel_fahrstunden, 1),
            "km": round(hotel_km),
        },
        "heimfahrt": {
            "sprit": round(heim_sprit, 2),
            "spesen": round(heim_spesen, 2),
            "gesamt": round(heim_gesamt, 2),
            "fahrstunden": round(heim_fahrstunden, 1),
            "km": round(heim_km),
        },
        "ersparnis_heimfahrt": round(hotel_gesamt - heim_gesamt, 2),
        "mehr_fahrstunden": round(heim_fahrstunden - hotel_fahrstunden, 1),
    }


def vergleich_text(v: dict, personen: int) -> str:
    """Stellt die Gegenüberstellung als Tabelle dar."""
    h, f = v["hotel"], v["heimfahrt"]
    zeilen = [
        f"| Posten | Hotel | Täglich heim |",
        "|---|---|---|",
        f"| Zimmer | {h['zimmer']:.2f} EUR | – |",
        f"| Diesel | {h['sprit']:.2f} EUR ({h['km']} km) "
        f"| {f['sprit']:.2f} EUR ({f['km']} km) |",
        f"| Verpflegungspauschale | {h['spesen']:.2f} EUR | {f['spesen']:.2f} EUR |",
        f"| **Summe** | **{h['gesamt']:.2f} EUR** | **{f['gesamt']:.2f} EUR** |",
        f"| Fahrzeit | {h['fahrstunden']:.1f} h | {f['fahrstunden']:.1f} h |",
        "",
    ]
    if not v["zumutbar"]:
        zeilen.append(
            f"**Heimfahren scheidet aus**: {v['fahrzeit_taeglich_h']:.1f} Stunden "
            f"Fahrt pro Mann und Tag, dazu die Montage. Über "
            f"{v['zumutbar_grenze_h']:.0f} Stunden wird das nichts, auch wenn die "
            f"Rechnung unten es günstiger aussehen lässt."
        )
    elif v["ersparnis_heimfahrt"] > 0:
        zeilen.append(
            f"Heimfahren spart {v['ersparnis_heimfahrt']:.2f} EUR, kostet aber "
            f"{v['mehr_fahrstunden']:.1f} Stunden mehr Fahrzeit, also "
            f"{v['fahrzeit_taeglich_h']:.1f} Stunden pro Mann und Tag."
        )
    else:
        zeilen.append(
            f"Das Hotel ist um {abs(v['ersparnis_heimfahrt']):.2f} EUR günstiger "
            f"und spart {abs(v['mehr_fahrstunden']):.1f} Stunden Fahrzeit."
        )
    zeilen.append(
        f"Gerechnet mit {v['dieselpreis']:.2f} EUR je Liter, {v['verbrauch']:.1f} l/100 km, "
        f"{v['strecke_km']:.0f} km einfache Strecke, {v['tempo_kmh']:.0f} km/h im "
        f"Schnitt und {v['arbeitstage']} Arbeitstagen. Die Fahrzeit ist nur "
        "ausgewiesen, nicht als Kosten eingerechnet."
    )
    return "\n".join(zeilen)


def lade_buchungen() -> list[dict]:
    pfad = hotelordner() / "buchungen.yaml"
    if not pfad.exists():
        return []
    return lade_yaml(pfad).get("buchungen", []) or []


def speichere_buchung(eintrag: dict) -> Path:
    """Hängt eine Buchung an die Historie an.

    Die Historie ist der eigentliche Vorteil gegenüber jeder Portalsuche:
    Beim nächsten Einsatz am selben Ort steht da, wo es gepasst hat und wo nicht.
    """
    pfad = hotelordner() / "buchungen.yaml"
    pfad.parent.mkdir(parents=True, exist_ok=True)
    bestand = lade_buchungen()
    bestand.append(eintrag)
    with pfad.open("w", encoding="utf-8") as f:
        yaml.safe_dump(
            {"buchungen": bestand}, f, allow_unicode=True, sort_keys=False
        )
    return pfad


def bekannte_hotels(baustelle: dict) -> list[dict]:
    """Frühere Buchungen an derselben Baustelle, neueste zuerst."""
    kuerzel = _normalisiere(baustelle.get("kuerzel", ""))
    kurzname = _normalisiere(baustelle.get("kurzname", ""))
    passend = [
        b
        for b in lade_buchungen()
        if _normalisiere(b.get("baustelle", "")) in {kuerzel, kurzname}
    ]
    return list(reversed(passend))
