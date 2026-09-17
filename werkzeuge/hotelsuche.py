#!/usr/bin/env python3
"""Hotelsuche für Monteure – Auftrag bauen, Treffer auswerten, Buchung merken.

Die eigentliche Verfügbarkeitsabfrage macht Claude über den Booking-Zugang.
Dieses Skript liefert davor und danach die Arbeit, die reproduzierbar sein
muss: Stammdaten auflösen, Entfernungen rechnen, Kriterien anwenden.

    python3 werkzeuge/hotelsuche.py auftrag BHV 12.10.2026 16.10.2026 --monteure MK TS
    python3 werkzeuge/hotelsuche.py auswerten <auftrag.json> <treffer.json>
    python3 werkzeuge/hotelsuche.py anfrage <auftrag.json> --hotel "Hotel Amaris"
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
    direkt_ab = hotels._zahl(kriterien.get("direktanfrage_ab_naechten"), 5)

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
        "direktanfrage_noetig": anzahl_naechte >= direkt_ab,
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
    if auftrag["direktanfrage_noetig"]:
        zeilen.append(
            f"Direktanfrage: ja – {z['naechte']} Nächte, "
            "Wochenpauschale beim Hotel erfragen"
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


def befehl_auswerten(args: argparse.Namespace) -> int:
    auftrag = json.loads(Path(args.auftrag).read_text(encoding="utf-8"))
    roh = json.loads(Path(args.treffer).read_text(encoding="utf-8"))
    rohtreffer = roh.get("accommodations", roh) if isinstance(roh, dict) else roh

    baustelle = dict(auftrag["baustelle"])
    baustelle["max_entfernung_km"] = auftrag["suche"]["radius_km"]
    baustelle["max_preis_pro_nacht"] = auftrag["suche"]["max_preis_pro_nacht"]

    treffer = hotels.auswerten(
        rohtreffer,
        baustelle,
        zimmer=auftrag["zimmer"],
        anzahl_naechte=auftrag["zeitraum"]["naechte"],
    )

    print(hotels.uebersicht(treffer, anzahl=args.anzahl))

    geeignete = [t for t in treffer if t.geeignet]
    if geeignete:
        bester = geeignete[0]
        print()
        print(
            "Kosten Platz 1: "
            + hotels.kostenschaetzung(
                bester, auftrag["zimmer"], auftrag["zeitraum"]["naechte"]
            )
        )
        vorschlaege = geeignete[: args.anzahl]
        print(
            "Vor dem Buchen klären: Durchfahrtshöhe bei "
            + ", ".join(t.name for t in vorschlaege)
        )
        if auftrag["suche"].get("fruehstueck_ab"):
            print(
                f"Ebenfalls klären: Frühstück ab "
                f"{auftrag['suche']['fruehstueck_ab']} Uhr."
            )

        _heimfahrt_zeigen(auftrag, bester.preis_pro_nacht)

    if args.ids:
        print()
        print("Hotel-IDs: " + ", ".join(str(t.hotel_id) for t in geeignete[: args.anzahl]))
    return 0


def befehl_anfrage(args: argparse.Namespace) -> int:
    """Füllt den Mailtext für die Direktanfrage beim Hotel.

    Lohnt sich ab etwa fünf Nächten: Wochen- und Monteurpauschalen liegen
    regelmäßig unter dem Portalpreis. Die drei Fragen, an denen eine Buchung
    scheitert - Frühstückszeit, Durchfahrtshöhe, Storno - stehen ohnehin in
    keinem Portal und sind hier gleich mit drin.
    """
    auftrag = json.loads(Path(args.auftrag).read_text(encoding="utf-8"))
    kriterien = hotels.lade_kriterien()
    absender = kriterien.get("absender") or {}

    fahrzeuge = {m.get("fahrzeug", "") for m in auftrag["besetzung"] if m.get("fahrzeug")}

    werte = {
        "hotel": args.hotel or "",
        "ort": auftrag["baustelle"].get("ort")
        or auftrag["baustelle"].get("kurzname", ""),
        "anreise": auftrag["zeitraum"]["anreise"],
        "abreise": auftrag["zeitraum"]["abreise"],
        "naechte": str(auftrag["zeitraum"]["naechte"]),
        "zimmer": str(auftrag["zimmer"]),
        "fahrzeuge": str(auftrag["zimmer"]),
        "fruehstueck_ab": auftrag["suche"].get("fruehstueck_ab") or "6:00",
        # Eine Wochenpauschale bei vier Nächten zu erfragen wirkt unbedacht.
        # Der Absatz erscheint erst ab der Dauer, ab der sie sich lohnt.
        "pauschale": "ja"
        if auftrag["zeitraum"]["naechte"]
        >= hotels._zahl(kriterien.get("direktanfrage_ab_naechten"), 5)
        else "",
        "hinweis": args.hinweis or "",
        "absender": args.absender or absender.get("name", ""),
        "firma": args.firma or absender.get("firma", ""),
    }
    if fahrzeuge:
        werte["fahrzeuge"] = f"{auftrag['zimmer']} ({', '.join(sorted(fahrzeuge))})"

    vorlage = repowurzel() / "vorlagen" / "hotelanfrage" / "anfrage.md"
    text = ersetze_in_markdown(vorlage.read_text(encoding="utf-8"), werte)

    if not werte["absender"] or not werte["firma"]:
        print(
            "Hinweis: Absender und Firma fehlen. In hotels/kriterien.yaml unter "
            "absender: eintragen oder mit --absender/--firma mitgeben.\n",
            file=sys.stderr,
        )

    if args.ziel:
        ziel = Path(args.ziel)
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_text(text, encoding="utf-8")
        print(f"Anfrage: {ziel}")
    else:
        print(text)
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
    p_auftrag.add_argument("--json", help="Auftrag zusätzlich als JSON ablegen")
    p_auftrag.set_defaults(funktion=befehl_auftrag)

    p_aus = unter.add_parser("auswerten", help="Booking-Treffer bewerten und sortieren")
    p_aus.add_argument("auftrag", help="JSON aus dem Befehl auftrag")
    p_aus.add_argument("treffer", help="JSON-Antwort der Hotelsuche")
    p_aus.add_argument("--anzahl", type=int, default=5)
    p_aus.add_argument("--ids", action="store_true", help="Hotel-IDs mit ausgeben")
    p_aus.set_defaults(funktion=befehl_auswerten)

    p_anfrage = unter.add_parser("anfrage", help="Mailtext für die Direktanfrage")
    p_anfrage.add_argument("auftrag", help="JSON aus dem Befehl auftrag")
    p_anfrage.add_argument("--hotel", help="nur zur Ablage, steht nicht im Text")
    p_anfrage.add_argument("--absender", help="überschreibt kriterien.yaml")
    p_anfrage.add_argument("--firma", help="überschreibt kriterien.yaml")
    p_anfrage.add_argument("--hinweis", help="Zusatz ans Hotel, z. B. späte Anreise")
    p_anfrage.add_argument("--ziel", help="Datei statt Ausgabe auf der Konsole")
    p_anfrage.set_defaults(funktion=befehl_anfrage)

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
