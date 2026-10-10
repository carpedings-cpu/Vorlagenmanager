#!/usr/bin/env python3
"""Hotelsuche für Monteure – Auftrag bauen, Treffer auswerten, Buchung merken.

Die eigentliche Verfügbarkeitsabfrage macht Claude über den Booking-Zugang.
Dieses Skript liefert davor und danach die Arbeit, die reproduzierbar sein
muss: Stammdaten auflösen, Entfernungen rechnen, Kriterien anwenden.

    python3 werkzeuge/hotelsuche.py auftrag BHV 12.10.2026 16.10.2026 --monteure MK TS
    python3 werkzeuge/hotelsuche.py auswerten <auftrag.json> <treffer.json>
    python3 werkzeuge/hotelsuche.py anfrage <auftrag.json> --vergleichspreis 89
    python3 werkzeuge/hotelsuche.py kostenuebernahme <auftrag.json> --hotel "Hotel Amaris" --preis 79
    python3 werkzeuge/hotelsuche.py buchen <auftrag.json> --hotel "Hotel Amaris" --preis 89.50
    python3 werkzeuge/hotelsuche.py baustellen
    python3 werkzeuge/hotelsuche.py monteure
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import hotels  # noqa: E402
import hotelpost  # noqa: E402
from kern import ersetze_in_markdown, repowurzel  # noqa: E402


def _auftrag_bauen(args: argparse.Namespace) -> dict:
    baustelle = hotels.finde_baustelle(args.baustelle)
    kriterien = hotels.lade_kriterien()
    besetzung = hotels.finde_monteure(args.monteure) if args.monteure else []

    anzahl_naechte = hotels.naechte(args.von, args.bis)
    if anzahl_naechte < 1:
        raise ValueError(
            f"Abreise ({args.bis}) liegt nicht nach der Anreise ({args.von})."
        )

    zimmer = args.zimmer or len(besetzung) or 1

    radius = hotels._zahl(
        baustelle.get("max_entfernung_km") or kriterien.get("max_entfernung_km"), 15.0
    )

    # Entfernung zum Betriebssitz: Sie entscheidet, ob tägliches Heimfahren
    # überhaupt eine Alternative ist.
    sitz = kriterien.get("betriebssitz") or {}
    koord = baustelle.get("koordinaten") or {}
    heimweg_km = None
    if sitz.get("lat") and sitz.get("lon") and koord.get("lat") and koord.get("lon"):
        heimweg_km = round(
            hotels.fahrstrecke_km(
                hotels.luftlinie_km(
                    hotels._zahl(sitz["lat"]),
                    hotels._zahl(sitz["lon"]),
                    hotels._zahl(koord["lat"]),
                    hotels._zahl(koord["lon"]),
                )
            ),
            1,
        )
    # Direkt beim Hotel ist der Standard. Nur wenn die Anreise so nah ist,
    # dass eine Mail nicht rechtzeitig beantwortet wird, geht es übers Portal.
    vorlauf_tage = (hotels._als_datum(args.von) - date.today()).days
    mindestvorlauf = int(
        hotels._zahl(kriterien.get("direktbuchung_mindestvorlauf_tage"), 2)
    )
    pauschale_ab = hotels._zahl(kriterien.get("pauschale_ab_naechten"), 5)

    return {
        "baustelle": {
            "kuerzel": baustelle.get("kuerzel", ""),
            "kurzname": baustelle.get("kurzname", ""),
            "projektnummer": baustelle.get("projektnummer", ""),
            "adresse": f"{baustelle.get('strasse', '')}, "
            f"{baustelle.get('plz', '')} {baustelle.get('ort', '')}".strip(", "),
            "ort": baustelle.get("ort", ""),
            "koordinaten": baustelle.get("koordinaten", {}),
            "hinweis": baustelle.get("hinweis", ""),
        },
        "zeitraum": {
            "anreise": hotels.als_deutsch(args.von),
            "abreise": hotels.als_deutsch(args.bis),
            "anreise_iso": hotels.als_iso(args.von),
            "abreise_iso": hotels.als_iso(args.bis),
            "naechte": anzahl_naechte,
        },
        "besetzung": [
            {
                "kuerzel": m.get("kuerzel", ""),
                "name": m.get("name", ""),
                "fahrzeug": m.get("fahrzeug", ""),
                "hinweis": m.get("hinweis", ""),
            }
            for m in besetzung
        ],
        "zimmer": zimmer,
        "suche": {
            "radius_km": radius,
            "mindestbewertung": hotels._zahl(kriterien.get("mindestbewertung"), 8.0),
            "max_preis_pro_nacht": hotels._zahl(
                baustelle.get("max_preis_pro_nacht")
                if baustelle.get("max_preis_pro_nacht") is not None
                else kriterien.get("max_preis_pro_nacht"),
                0.0,
            ),
            "fruehstueck": bool(kriterien.get("fruehstueck", True)),
            "fruehstueck_ab": kriterien.get("fruehstueck_ab", ""),
            "freie_stornierung": bool(kriterien.get("freie_stornierung", True)),
            "parkplatz_pflicht": bool(kriterien.get("parkplatz_pflicht", True)),
            "zimmerart": kriterien.get("zimmerart", "Einzelzimmer"),
            "eigenes_bad": bool(kriterien.get("eigenes_bad", True)),
        },
        "heimweg_km": heimweg_km,
        "betriebssitz": sitz.get("ort", ""),
        "direktbuchung": vorlauf_tage >= mindestvorlauf,
        "vorlauf_tage": vorlauf_tage,
        "pauschale_erfragen": anzahl_naechte >= pauschale_ab,
        # Zwei Mann in einem Sprinter brauchen einen Stellplatz, nicht zwei.
        # Ohne Angabe ein Fahrzeug je Mann.
        "fahrzeuge": args.fahrzeuge or len(besetzung) or zimmer,
        "bekannt": hotels.bekannte_hotels(baustelle)[:3],
    }


def _auftrag_zeigen(auftrag: dict) -> str:
    b = auftrag["baustelle"]
    z = auftrag["zeitraum"]
    s = auftrag["suche"]
    besetzung = auftrag["besetzung"]

    zeilen = [
        f"Baustelle: {b['kurzname']} ({b['kuerzel']}), {b['adresse']}",
        f"Zeitraum:  {z['anreise']} bis {z['abreise']}, {z['naechte']} Nächte",
        f"Zimmer:    {auftrag['zimmer']} × {s['zimmerart']}, Dusche/WC im Zimmer",
    ]
    if besetzung:
        # Steht noch kein Name in den Stammdaten, bleibt es beim Kürzel,
        # statt eine leere Klammer hinzuschreiben.
        namen = ", ".join(
            f"{m['kuerzel']} ({m['name']})" if m.get("name") else m["kuerzel"]
            for m in besetzung
        )
        zeilen.append(f"Besetzung: {namen}")
    zeilen += [
        f"Radius:    {s['radius_km']:.0f} km um die Baustelle",
        f"Filter:    ab {s['mindestbewertung']:.1f} Bewertung"
        + (
            f", max. {s['max_preis_pro_nacht']:.0f} EUR/Nacht"
            if s["max_preis_pro_nacht"]
            else ""
        )
        + (", Frühstück" if s["fruehstueck"] else "")
        + (", freie Stornierung" if s["freie_stornierung"] else "")
        + (", Parkplatz" if s["parkplatz_pflicht"] else ""),
    ]
    if b["hinweis"]:
        zeilen.append(f"Hinweis:   {b['hinweis']}")
    for m in besetzung:
        if m["hinweis"]:
            zeilen.append(f"           {m['kuerzel']}: {m['hinweis']}")
    if auftrag.get("heimweg_km"):
        zeilen.append(
            f"Heimweg:   {auftrag['heimweg_km']:.0f} km ab "
            f"{auftrag.get('betriebssitz') or 'Betriebssitz'}, einfache Strecke"
        )
    if auftrag.get("direktbuchung", True):
        zeilen.append(
            "Buchung:   direkt beim Hotel, Anfrage als Mailentwurf"
            + (" mit Frage nach Wochenpauschale" if auftrag.get("pauschale_erfragen") else "")
        )
    else:
        zeilen.append(
            f"Buchung:   Portal oder Anruf – Anreise in {auftrag.get('vorlauf_tage', 0)} "
            "Tag(en), zu knapp für eine Mailanfrage"
        )
    if auftrag["bekannt"]:
        zeilen.append("Schon gebucht an dieser Baustelle:")
        for fruehere in auftrag["bekannt"]:
            bewertung = fruehere.get("fazit", "")
            zeilen.append(
                f"  - {fruehere.get('hotel', '?')}"
                + (f" – {bewertung}" if bewertung else "")
            )
    return "\n".join(zeilen)


def befehl_auftrag(args: argparse.Namespace) -> int:
    auftrag = _auftrag_bauen(args)
    if args.json:
        ziel = Path(args.json)
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_text(
            json.dumps(auftrag, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    print(_auftrag_zeigen(auftrag))
    if args.json:
        print(f"\nAuftrag: {args.json}")
    return 0


def _einlesen(pfad: str) -> list[dict]:
    """Liest eine Trefferdatei und erkennt am Format, aus welchem Portal sie ist.

    Trivago nennt das Haus `accommodation_name`, Booking `name`. Daran hängt,
    ob die Treffer vorher umgewandelt werden müssen; ein stumpfes Einlesen
    liefert sonst eine Liste von Häusern ohne Namen und ohne Preis.
    """
    roh = json.loads(Path(pfad).read_text(encoding="utf-8"))
    liste = roh.get("accommodations", roh) if isinstance(roh, dict) else roh
    if liste and isinstance(liste[0], dict) and "accommodation_name" in liste[0]:
        return hotels.normalisiere_trivago(liste)
    return liste


def befehl_auswerten(args: argparse.Namespace) -> int:
    auftrag = json.loads(Path(args.auftrag).read_text(encoding="utf-8"))
    pfade = args.treffer if isinstance(args.treffer, list) else [args.treffer]
    rohtreffer = []
    for pfad in pfade:
        rohtreffer.extend(_einlesen(pfad))

    baustelle = dict(auftrag["baustelle"])
    baustelle["max_entfernung_km"] = auftrag["suche"]["radius_km"]
    baustelle["max_preis_pro_nacht"] = auftrag["suche"]["max_preis_pro_nacht"]

    treffer = hotels.auswerten(
        rohtreffer,
        baustelle,
        zimmer=auftrag["zimmer"],
        anzahl_naechte=auftrag["zeitraum"]["naechte"],
    )
    if len(pfade) > 1:
        # Dasselbe Haus steht jetzt mehrfach in der Liste, einmal je Quelle.
        # Zusammenfassen und danach neu punkten, sonst stimmt die Rangfolge
        # nicht mehr zur zusammengefassten Zeile.
        treffer = hotels.zusammenfuehren(treffer)
        treffer = hotels.nachpunkten(treffer, baustelle)

    print(hotels.uebersicht(treffer, anzahl=args.anzahl))

    geeignete = [t for t in treffer if t.geeignet]
    if geeignete:
        print()
        print("Was der Einsatz kostet:")
        print(
            hotels.kostentabelle(
                geeignete[: args.anzahl],
                auftrag["zimmer"],
                auftrag["zeitraum"]["naechte"],
            )
        )
        print()
        if auftrag["suche"].get("fruehstueck_ab"):
            print(
                f"Vor dem Buchen klären: Frühstück ab "
                f"{auftrag['suche']['fruehstueck_ab']} Uhr."
            )

        # Gegen die Heimfahrt gerechnet wird der unterm Strich günstigste
        # Vorschlag, nicht Platz 1. Sonst sieht die Heimfahrt besser aus, als
        # sie ist.
        guenstigster = min(
            geeignete[: args.anzahl], key=lambda x: x.preis_pro_nacht
        )
        _heimfahrt_zeigen(auftrag, guenstigster.preis_pro_nacht)

    if args.ids:
        print()
        print("Hotel-IDs: " + ", ".join(str(t.hotel_id) for t in geeignete[: args.anzahl]))
    return 0


def _ausgeben(betreff: str, text: str, args: argparse.Namespace, extra: dict | None = None) -> None:
    """Gibt eine Mail als Text oder als JSON für den Postfachentwurf aus."""
    if getattr(args, "json", None):
        daten = {"an": args.an or "", "betreff": betreff, "text": text}
        daten.update(extra or {})
        ziel = Path(args.json)
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_text(json.dumps(daten, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Mail als JSON: {ziel}")
    else:
        print(f"Betreff: {betreff}\n")
        print(text)


def befehl_anfrage(args: argparse.Namespace) -> int:
    """Zimmeranfrage für die Direktbuchung beim Hotel.

    Der Standardweg, nicht mehr nur ab fünf Nächten: Ohne Portal spart das Haus
    die Provision, und die Fragen, an denen eine Buchung scheitert, stehen in
    keinem Portal. Frühstückszeit, Parkplatz, Storno.
    """
    auftrag = json.loads(Path(args.auftrag).read_text(encoding="utf-8"))
    kriterien = hotels.lade_kriterien()
    betreff, text = hotelpost.anfrage(
        auftrag, kriterien, vergleichspreis=args.vergleichspreis, hinweis=args.hinweis or ""
    )
    fehlend = hotelpost.fehlende_angaben(hotelpost.absender(kriterien), hotelpost.PFLICHT_ANFRAGE)
    if fehlend:
        print(
            "Hinweis: Im Absender fehlt " + ", ".join(fehlend)
            + ". In hotels/kriterien.yaml unter absender: eintragen.\n",
            file=sys.stderr,
        )
    if not auftrag.get("direktbuchung", True):
        print(
            f"Hinweis: Anreise in {auftrag.get('vorlauf_tage', 0)} Tag(en). Bis die "
            "Antwort da ist, kann das Zimmer weg sein. Besser anrufen.\n",
            file=sys.stderr,
        )
    _ausgeben(betreff, text, args, {"hotel": args.hotel or ""})
    return 0


def befehl_kostenuebernahme(args: argparse.Namespace) -> int:
    """Kostenübernahmeerklärung als PDF plus Begleitmail.

    Erst nach der Zusage des Hotels: Der Preis ist der bestätigte, nicht der
    aus der Suche, und die Namen der Gäste stehen fest.
    """
    auftrag = json.loads(Path(args.auftrag).read_text(encoding="utf-8"))
    ergebnis = hotelpost.kostenuebernahme(
        auftrag,
        hotel=args.hotel,
        preis=args.preis,
        gaeste=args.gaeste,
        bestaetigung=args.bestaetigung or "",
        hotel_adresse=args.hotel_adresse or "",
        parkplatz_je_nacht=args.parkplatz or 0.0,
    )
    ordner = Path(args.ziel) if args.ziel else hotels.hotelordner() / "post"
    ordner.mkdir(parents=True, exist_ok=True)
    html_pfad = ordner / f"{ergebnis['dateiname']}.html"
    html_pfad.write_text(ergebnis["html"], encoding="utf-8")
    pdf_pfad = ordner / f"{ergebnis['dateiname']}.pdf"
    hat_pdf = hotelpost.html_zu_pdf(ergebnis["html"], pdf_pfad)

    for hinweis in ergebnis["hinweise"]:
        print(f"Hinweis: {hinweis}", file=sys.stderr)
    print(f"Dokument: {pdf_pfad if hat_pdf else html_pfad}")
    if not hat_pdf:
        print(
            "Kein PDF: Playwright fehlt. Die HTML-Datei im Browser öffnen und "
            "als PDF drucken.",
            file=sys.stderr,
        )
    print(f"Gesamt voraussichtlich: {hotelpost.euro(ergebnis['gesamt'])} EUR\n")
    _ausgeben(
        ergebnis["betreff"], ergebnis["text"], args,
        {"anhang": str(pdf_pfad if hat_pdf else html_pfad), "hotel": args.hotel},
    )
    return 0


def _heimfahrt_zeigen(auftrag: dict, preis_pro_nacht: float) -> None:
    """Rechnet die Heimfahrt gegen, sobald die Baustelle in Reichweite liegt."""
    heimweg = hotels._zahl(auftrag.get("heimweg_km"), 0)
    if not heimweg:
        return
    kriterien = hotels.lade_kriterien()
    grenze = hotels._zahl(kriterien.get("heimfahrt_pruefen_bis_km"), 150)
    if heimweg > grenze:
        return

    vergleich = hotels.heimfahrt_vergleich(
        # Der Heimweg steht schon als Strecke im Auftrag, nicht als Luftlinie
        entfernung_km=heimweg / hotels.UMWEGFAKTOR,
        anzahl_naechte=auftrag["zeitraum"]["naechte"],
        personen=auftrag["zimmer"],
        preis_pro_nacht=preis_pro_nacht,
        kriterien=kriterien,
    )
    print()
    print(f"Heimfahren statt übernachten ({heimweg:.0f} km einfach):")
    print(hotels.vergleich_text(vergleich, auftrag["zimmer"]))


def befehl_buchen(args: argparse.Namespace) -> int:
    auftrag = json.loads(Path(args.auftrag).read_text(encoding="utf-8"))
    eintrag = {
        "baustelle": auftrag["baustelle"]["kuerzel"] or auftrag["baustelle"]["kurzname"],
        "projektnummer": auftrag["baustelle"].get("projektnummer", ""),
        "hotel": args.hotel,
        "anreise": auftrag["zeitraum"]["anreise"],
        "abreise": auftrag["zeitraum"]["abreise"],
        "naechte": auftrag["zeitraum"]["naechte"],
        "zimmer": auftrag["zimmer"],
        "monteure": [m["kuerzel"] for m in auftrag["besetzung"]],
        "preis_pro_nacht": args.preis,
        # Der Gesamtpreis kommt bevorzugt aus dem Angebot. Aus dem gerundeten
        # Nachtpreis hochgerechnet weicht er sonst um Cents ab, und genau das
        # fällt beim Abgleich mit der Rechnung auf.
        "gesamt": args.gesamt
        or (
            round(args.preis * auftrag["zimmer"] * auftrag["zeitraum"]["naechte"], 2)
            if args.preis
            else None
        ),
        "gebucht_am": date.today().strftime(hotels.DATUMSFORMAT),
        "fazit": args.fazit or "",
    }
    pfad = hotels.speichere_buchung(eintrag)
    print(f"Eingetragen in {pfad}:")
    print(
        f"  {eintrag['hotel']}, {eintrag['anreise']} bis {eintrag['abreise']}, "
        f"{eintrag['zimmer']} Zimmer"
        + (f", gesamt {eintrag['gesamt']:.2f} EUR" if eintrag["gesamt"] else "")
    )
    return 0


def befehl_baustellen(_: argparse.Namespace) -> int:
    for b in hotels.lade_baustellen():
        koord = b.get("koordinaten") or {}
        fehlt = "" if koord.get("lat") and koord.get("lon") else "  ⚠ Koordinaten fehlen"
        print(
            f"{b.get('kuerzel', '?'):6} {b.get('kurzname', '?'):32} "
            f"{b.get('plz', '')} {b.get('ort', '')}{fehlt}"
        )
    return 0


def befehl_monteure(_: argparse.Namespace) -> int:
    for m in hotels.lade_monteure():
        print(
            f"{m.get('kuerzel', '?'):6} {m.get('name', '?'):28} "
            f"{m.get('fahrzeug', '')}"
        )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    unter = parser.add_subparsers(dest="befehl", required=True)

    p_auftrag = unter.add_parser("auftrag", help="Suchauftrag aus den Stammdaten bauen")
    p_auftrag.add_argument("baustelle", help="Kürzel, Projektnummer oder Kurzname")
    p_auftrag.add_argument("von", help="Anreise, TT.MM.JJJJ")
    p_auftrag.add_argument("bis", help="Abreise, TT.MM.JJJJ")
    p_auftrag.add_argument("--monteure", nargs="*", default=[], help="Kürzel")
    p_auftrag.add_argument("--zimmer", type=int, help="falls ohne Monteurliste")
    p_auftrag.add_argument(
        "--fahrzeuge", type=int,
        help="Stellplätze; ohne Angabe einer je Mann",
    )
    p_auftrag.add_argument("--json", help="Auftrag zusätzlich als JSON ablegen")
    p_auftrag.set_defaults(funktion=befehl_auftrag)

    p_aus = unter.add_parser("auswerten", help="Treffer bewerten und sortieren")
    p_aus.add_argument("auftrag", help="JSON aus dem Befehl auftrag")
    p_aus.add_argument(
        "treffer",
        nargs="+",
        help="eine oder mehrere JSON-Antworten; Trivago wird am Format erkannt",
    )
    p_aus.add_argument("--anzahl", type=int, default=5)
    p_aus.add_argument("--ids", action="store_true", help="Hotel-IDs mit ausgeben")
    p_aus.set_defaults(funktion=befehl_auswerten)

    p_anfrage = unter.add_parser("anfrage", help="Zimmeranfrage für die Direktbuchung")
    p_anfrage.add_argument("auftrag", help="JSON aus dem Befehl auftrag")
    p_anfrage.add_argument("--hotel", help="Name des Hotels, steht nur in der JSON-Ausgabe")
    p_anfrage.add_argument("--an", help="Mailadresse des Hotels, für die JSON-Ausgabe")
    p_anfrage.add_argument(
        "--vergleichspreis", type=float,
        help="Portalpreis je Zimmer und Nacht; steht als Verhandlungsbasis in der Mail",
    )
    p_anfrage.add_argument("--hinweis", help="Zusatz ans Hotel, z. B. späte Anreise")
    p_anfrage.add_argument("--json", help="Betreff und Text als JSON ablegen")
    p_anfrage.set_defaults(funktion=befehl_anfrage)

    p_kosten = unter.add_parser(
        "kostenuebernahme", help="Kostenübernahme als PDF, nach Zusage des Hotels"
    )
    p_kosten.add_argument("auftrag", help="JSON aus dem Befehl auftrag")
    p_kosten.add_argument("--hotel", required=True)
    p_kosten.add_argument(
        "--preis", type=float, required=True,
        help="vom Hotel bestätigter Preis je Zimmer und Nacht inkl. Frühstück",
    )
    p_kosten.add_argument("--gaeste", nargs="+", help="Namen; ohne Angabe aus dem Auftrag")
    p_kosten.add_argument("--bestaetigung", help="Buchungsnummer des Hotels")
    p_kosten.add_argument("--hotel-adresse", help="Straße, PLZ Ort, kommagetrennt")
    p_kosten.add_argument(
        "--parkplatz", type=float, help="Parkgebühr je Fahrzeug und Nacht, wenn extra"
    )
    p_kosten.add_argument("--an", help="Mailadresse des Hotels, für die JSON-Ausgabe")
    p_kosten.add_argument("--ziel", help="Ordner für PDF; Standard hotels/post/")
    p_kosten.add_argument("--json", help="Betreff, Text und Anhang als JSON ablegen")
    p_kosten.set_defaults(funktion=befehl_kostenuebernahme)

    p_buchen = unter.add_parser("buchen", help="Buchung in der Historie festhalten")
    p_buchen.add_argument("auftrag", help="JSON aus dem Befehl auftrag")
    p_buchen.add_argument("--hotel", required=True)
    p_buchen.add_argument("--preis", type=float, default=0.0, help="EUR pro Nacht")
    p_buchen.add_argument("--gesamt", type=float, help="Angebotssumme, falls bekannt")
    p_buchen.add_argument("--fazit", help="z. B. 'Parkplatz eng, Frühstück ab 5:30'")
    p_buchen.set_defaults(funktion=befehl_buchen)

    unter.add_parser("baustellen", help="hinterlegte Baustellen").set_defaults(
        funktion=befehl_baustellen
    )
    unter.add_parser("monteure", help="hinterlegte Monteure").set_defaults(
        funktion=befehl_monteure
    )

    args = parser.parse_args()
    try:
        return args.funktion(args)
    except (FileNotFoundError, LookupError, ValueError) as fehler:
        print(f"Fehler: {fehler}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
