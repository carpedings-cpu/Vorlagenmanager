"""Bausteine für die Monteur-Hotelsuche.

Die Live-Suche selbst läuft nicht hier, sondern über den Booking-Zugang von
Claude. Dieses Modul macht das Drumherum, das eine Portalsuche nicht kann:

* Baustellen und Monteure aus den Stammdaten holen
* Entfernung Hotel–Baustelle rechnen
* aus der Ausstattungsliste ableiten, ob ein Sprinter dort parken kann
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

# Höhe eines Sprinters mit Hochdach. Normale Tiefgaragen liegen bei 2,00 m,
# großzügig gebaute bei 2,10 m. Alles darüber braucht einen Platz im Freien.
SPRINTERHOEHE_M = 2.60
HOEHENGRENZE_PARKHAUS_M = 2.00


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
    return _lade_stammdatei("monteure.yaml", "monteure")


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

# Was in der Ausstattungsliste von Booking für bzw. gegen einen Stellplatz
# spricht, auf dem ein Sprinter mit Hochdach steht.
PARKEN_EBENERDIG = (
    "privatparkplatz",
    "parken vor ort",
    "parkplatz inbegriffen",
    "kostenlose parkplätze",
    "kostenloser parkplatz",
    "überdachte parkplätze",
)
PARKEN_HOEHENRISIKO = ("parkhaus", "tiefgarage", "garage")
PARKEN_NUR_STRASSE = ("parkplätze an der straße", "öffentliche parkplätze")
PARKEN_ALLGEMEIN = ("parkplatz", "parken")


@dataclass
class Parkurteil:
    status: str  # "ok", "pruefen", "kritisch"
    hinweis: str

    @property
    def zeichen(self) -> str:
        return {"ok": "✅", "pruefen": "🔍", "kritisch": "⛔"}[self.status]


def beurteile_parkplatz(
    ausstattung: list[str], fahrzeughoehe_m: float = SPRINTERHOEHE_M
) -> Parkurteil:
    """Leitet aus der Ausstattungsliste ab, ob das Fahrzeug dort stehen kann.

    Booking kennt nur „Parkplatz vorhanden". Ob der Stellplatz ebenerdig ist
    oder in einer Tiefgarage mit 2,00 m Durchfahrtshöhe liegt, steht in keinem
    Filter – macht aber den Unterschied zwischen buchen und nicht buchen.

    Fährt die Truppe flach (Vito, Transporter ohne Hochdach), ist ein Parkhaus
    kein Ausschluss mehr, sondern nur noch ein Punkt zum Nachfragen.
    """
    klein = [str(a).lower() for a in ausstattung]
    passt_ins_parkhaus = fahrzeughoehe_m <= HOEHENGRENZE_PARKHAUS_M

    def enthaelt(begriffe: tuple[str, ...]) -> bool:
        return any(b in eintrag for eintrag in klein for b in begriffe)

    ebenerdig = enthaelt(PARKEN_EBENERDIG)
    hoehenrisiko = enthaelt(PARKEN_HOEHENRISIKO)
    nur_strasse = enthaelt(PARKEN_NUR_STRASSE)
    irgendein = enthaelt(PARKEN_ALLGEMEIN)

    if ebenerdig and not hoehenrisiko:
        # Praxisfall Limehome Berlin: "Privatparkplatz, Parken vor Ort", kein
        # Wort von Parkhaus, tatsächlich 2,00 m Schranke. Die Ausstattungsliste
        # kennt keine Durchfahrtshöhe, also wird hier auch keine behauptet.
        return Parkurteil("ok", "Stellplatz am Haus, Höhe unbestätigt")
    if ebenerdig and hoehenrisiko:
        return Parkurteil(
            "pruefen",
            f"Stellplatz und Parkhaus angegeben, Durchfahrtshöhe für "
            f"{fahrzeughoehe_m:.2f} m erfragen",
        )
    if hoehenrisiko:
        if passt_ins_parkhaus:
            return Parkurteil(
                "pruefen",
                f"nur Parkhaus/Tiefgarage, bei {fahrzeughoehe_m:.2f} m machbar, "
                "Höhe bestätigen lassen",
            )
        return Parkurteil(
            "kritisch",
            f"nur Parkhaus/Tiefgarage, für {fahrzeughoehe_m:.2f} m meist zu niedrig",
        )
    if nur_strasse:
        return Parkurteil("kritisch", "nur Parken am Straßenrand, kein eigener Platz")
    if irgendein:
        return Parkurteil("pruefen", "Parkplatz genannt, Art unklar, nachfragen")
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
    fahrzeughoehe_m: float = SPRINTERHOEHE_M,
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
    max_nacht = _zahl(kriterien.get("max_preis_pro_nacht"), 0.0)
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
        park = beurteile_parkplatz(ausstattung, fahrzeughoehe_m)

        gruende = []
        if entfernung > max_entfernung:
            gruende.append(f"{entfernung:.1f} km, mehr als {max_entfernung:.0f} km")
        # mindestbewertung 0 heißt: Bewertung ist egal. Dann fliegt ein noch
        # unbewertetes Haus auch nicht wegen der fehlenden Bewertung raus.
        if not hat_bewertung and min_bewertung > 0:
            gruende.append("keine Bewertung vorhanden, vor dem Buchen ansehen")
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
                hotel_id=int(_zahl(roh.get("id"))),
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

    _punkte_vergeben(ergebnis, kriterien, max_entfernung)
    ergebnis.sort(key=lambda t: (not t.geeignet, -t.punkte))
    return ergebnis


def _punkte_vergeben(
    treffer: list[Treffer], kriterien: dict, max_entfernung: float
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
    bezug = _zahl(kriterien.get("max_preis_pro_nacht"), 0.0) or teuerst

    for t in treffer:
        nah = 1 - min(t.entfernung_km / max_entfernung, 1.0) if max_entfernung else 0.0
        if bezug > 0 and t.preis_pro_nacht > 0:
            guenstig = max(0.0, 1 - t.preis_pro_nacht / bezug)
        else:
            guenstig = 1.0
        gut = max(0.0, min((t.bewertung - 7.0) / 3.0, 1.0))
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
        "| # | Hotel | Entfernung | EUR/Nacht | Bewertung | Parkplatz |",
        "|---|---|---|---|---|---|",
    ]
    for nr, t in enumerate(geeignete, 1):
        zeilen.append(
            f"| {nr} | [{t.name}]({t.url}) | {t.entfernung_km:.1f} km "
            f"(ca. {t.fahrzeit_min} min) | {t.preis_pro_nacht:.2f} | "
            + (f"{t.bewertung:.1f} ({t.anzahl_bewertungen})" if t.hat_bewertung
               else "ohne Bewertung")
            + " | "
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
        "Die Durchfahrtshöhe steht in keiner Ausstattungsliste. Vor dem Buchen "
        "bei jedem Haus erfragen, auch bei ✅."
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


# --- Buchungen festhalten --------------------------------------------------


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
