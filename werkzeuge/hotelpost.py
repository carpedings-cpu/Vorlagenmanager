"""Post ans Hotel: Zimmeranfrage und Kostenübernahme.

Beide Schreiben entstehen hier als fertiger Text, die Kostenübernahme dazu als
PDF im KPC-Design. Verschickt wird nichts: Claude legt daraus einen Entwurf im
Postfach an, Diana liest gegen und schickt ab.

Warum direkt beim Hotel und nicht über das Portal: Booking und Co. nehmen dem
Haus 15 bis 18 Prozent Provision ab. Seit dem BGH-Urteil von 2021 (KVR 54/20)
darf ein Hotel direkt günstiger anbieten, und die meisten tun es, wenn man
fragt und den Portalpreis nennt.
"""

from __future__ import annotations

import base64
import glob
import html
import mimetypes
from datetime import date
from pathlib import Path

import hotels
from kern import ersetze_in_markdown, repowurzel

# Was auf einem Geschäftsbrief einer GmbH stehen muss (§ 35a GmbHG), dazu was
# das Hotel braucht, um zurückzuschreiben und die Rechnung zu stellen.
PFLICHT_GESCHAEFTSBRIEF = {
    "firma": "Firma mit Rechtsform",
    "ort": "Sitz",
    "registergericht": "Registergericht",
    "hrb": "Registernummer",
    "geschaeftsfuehrung": "Geschäftsführung",
}
PFLICHT_ANFRAGE = {
    "name": "Name",
    "firma": "Firma",
    "email": "E-Mail für die Antwort",
}

ABSENDER_FELDER = (
    "name", "funktion", "telefon", "email", "firma", "strasse", "plz", "ort",
    "telefon_zentrale", "web", "registergericht", "hrb", "ust_id",
    "geschaeftsfuehrung", "rechnung_email", "logo", "unterschrift",
)


def absender(kriterien: dict | None = None) -> dict:
    """Absenderangaben mit allen Feldern, fehlende als leere Zeichenkette."""
    kriterien = kriterien if kriterien is not None else hotels.lade_kriterien()
    roh = kriterien.get("absender") or {}
    return {feld: str(roh.get(feld) or "").strip() for feld in ABSENDER_FELDER}


def fehlende_angaben(abs_: dict, pflicht: dict) -> list[str]:
    return [bezeichnung for feld, bezeichnung in pflicht.items() if not abs_.get(feld)]


def euro(betrag: float) -> str:
    """1234.5 -> "1.234,50". Hotels lesen deutsche Zahlen."""
    text = f"{betrag:,.2f}"
    return text.replace(",", "§").replace(".", ",").replace("§", ".")


def mail_zerlegen(text: str) -> tuple[str, str]:
    """Trennt die erste Zeile "Betreff: ..." vom Text."""
    zeilen = text.strip("\n").split("\n")
    if zeilen and zeilen[0].lower().startswith("betreff:"):
        betreff = zeilen[0].split(":", 1)[1].strip()
        rumpf = "\n".join(zeilen[1:]).strip("\n")
        return betreff, rumpf + "\n"
    return "", text


def _signatur(abs_: dict) -> dict:
    adresse = ", ".join(
        teil for teil in (abs_["strasse"], f"{abs_['plz']} {abs_['ort']}".strip()) if teil
    )
    return {
        "absender": abs_["name"],
        "funktion": abs_["funktion"],
        "firma": abs_["firma"],
        "adresszeile": adresse,
        "telefonzeile": f"Tel. {abs_['telefon']}" if abs_["telefon"] else "",
        "email": abs_["email"],
        "strasse": abs_["strasse"],
        "plz": abs_["plz"],
        # "ort" ist in der Anfrage schon der Baustellenort.
        "ort_firma": abs_["ort"],
    }


def _anzahl(n: int, einzahl: str, mehrzahl: str) -> str:
    return f"{n} {einzahl if n == 1 else mehrzahl}"


def _rechnungsvermerk(auftrag: dict) -> str:
    b = auftrag["baustelle"]
    teile = []
    if b.get("projektnummer"):
        teile.append(f"Projekt {b['projektnummer']}")
    teile.append(b.get("kuerzel") or b.get("kurzname") or "")
    if b.get("kurzname") and b.get("kuerzel"):
        teile.append(b["kurzname"])
    return " · ".join(t for t in teile if t)


# --- Anfrage -----------------------------------------------------------------


def anfrage(
    auftrag: dict,
    kriterien: dict | None = None,
    vergleichspreis: float | None = None,
    hinweis: str = "",
) -> tuple[str, str]:
    """Betreff und Text der Zimmeranfrage.

    Der Vergleichspreis ist der Portalpreis je Zimmer und Nacht. Er steht in
    der Mail, weil das Hotel dann weiß, was es schlagen muss, und weil es sich
    bei direkter Buchung die Provision spart.
    """
    kriterien = kriterien if kriterien is not None else hotels.lade_kriterien()
    abs_ = absender(kriterien)
    naechte = auftrag["zeitraum"]["naechte"]
    pauschale = auftrag.get("pauschale_erfragen")
    if pauschale is None:
        pauschale = naechte >= hotels._zahl(kriterien.get("pauschale_ab_naechten"), 5)
    fahrzeuge = int(auftrag.get("fahrzeuge") or auftrag["zimmer"])

    werte = {
        **_signatur(abs_),
        "ort": auftrag["baustelle"].get("ort") or auftrag["baustelle"].get("kurzname", ""),
        "anreise": auftrag["zeitraum"]["anreise"],
        "abreise": auftrag["zeitraum"]["abreise"],
        "naechte": str(naechte),
        "zimmer": str(auftrag["zimmer"]),
        "fahrzeuge": _anzahl(fahrzeuge, "Fahrzeug", "Fahrzeuge"),
        "fruehstueck_ab": auftrag["suche"].get("fruehstueck_ab") or "6:00",
        "vergleichspreis": euro(vergleichspreis) if vergleichspreis else "",
        "pauschale": "ja" if pauschale else "",
        "hinweis": hinweis,
    }
    vorlage = repowurzel() / "vorlagen" / "hotelanfrage" / "anfrage.md"
    return mail_zerlegen(ersetze_in_markdown(vorlage.read_text(encoding="utf-8"), werte))


# --- Kostenübernahme ---------------------------------------------------------


def _bild_als_daten(dateiname: str) -> str:
    """Bettet ein Bild aus dem Ordner hotels/ als data-URI ein, sonst ""."""
    if not dateiname:
        return ""
    pfad = hotels.hotelordner() / dateiname
    if not pfad.is_file():
        return ""
    art = mimetypes.guess_type(pfad.name)[0] or "image/png"
    inhalt = base64.b64encode(pfad.read_bytes()).decode("ascii")
    return f"data:{art};base64,{inhalt}"


def gaeste_aus_auftrag(auftrag: dict) -> list[str]:
    return [m["name"] for m in auftrag.get("besetzung", []) if m.get("name")]


def kostenuebernahme(
    auftrag: dict,
    hotel: str,
    preis: float,
    gaeste: list[str] | None = None,
    bestaetigung: str = "",
    hotel_adresse: str = "",
    parkplatz_je_nacht: float = 0.0,
    kriterien: dict | None = None,
    datum: date | None = None,
) -> dict:
    """Mailtext und HTML-Dokument der Kostenübernahmeerklärung.

    `preis` ist der vom Hotel bestätigte Preis je Zimmer und Nacht, nicht der
    aus der Suche: Was hier steht, unterschreibt die Firma.
    """
    kriterien = kriterien if kriterien is not None else hotels.lade_kriterien()
    abs_ = absender(kriterien)
    gaeste = [g for g in (gaeste or gaeste_aus_auftrag(auftrag)) if g.strip()]
    zimmer = int(auftrag["zimmer"])
    naechte = int(auftrag["zeitraum"]["naechte"])
    fahrzeuge = int(auftrag.get("fahrzeuge") or zimmer)
    datum = datum or date.today()

    zimmerkosten = preis * zimmer * naechte
    parkkosten = parkplatz_je_nacht * fahrzeuge * naechte
    vermerk = _rechnungsvermerk(auftrag)

    hinweise = []
    if len(gaeste) != zimmer:
        hinweise.append(
            f"{len(gaeste)} Gäste für {zimmer} Zimmer. Ein Zimmer pro Mann, "
            "bitte Namen prüfen."
        )
    fehlend = fehlende_angaben(abs_, PFLICHT_GESCHAEFTSBRIEF)
    if fehlend:
        hinweise.append(
            "Pflichtangaben für den Geschäftsbrief fehlen (§ 35a GmbHG): "
            + ", ".join(fehlend)
            + ". Eintragen in hotels/kriterien.yaml unter absender."
        )
    if not abs_["rechnung_email"]:
        hinweise.append("Keine Rechnungsadresse, es gilt die E-Mail des Absenders.")

    sig = _signatur(abs_)
    e = html.escape

    logo = _bild_als_daten(abs_["logo"])
    if logo:
        marke = f'<img src="{logo}" alt="{e(abs_["firma"])}">'
    else:
        wort = (abs_["firma"].split() or [""])[0]
        marke = f'<div class="wortmarke">{e(wort)}</div>'

    unterschrift = _bild_als_daten(abs_["unterschrift"])
    ohne_unterschrift = (
        "" if unterschrift
        else "Dieses Schreiben wurde elektronisch erstellt und ist ohne Unterschrift gültig."
    )

    register = ", ".join(t for t in (abs_["registergericht"], abs_["hrb"]) if t)
    if parkplatz_je_nacht:
        parkzeile = (
            f"{_anzahl(fahrzeuge, 'Stellplatz', 'Stellplätze')} zu {euro(parkplatz_je_nacht)} "
            "EUR je Nacht"
        )
    else:
        parkzeile = f"{_anzahl(fahrzeuge, 'Stellplatz', 'Stellplätze')}, im Preis enthalten"

    werte_html = {k: e(v) for k, v in sig.items()}
    werte_html.update({
        "hotel": e(hotel),
        "hotel_adresse_html": "<br>".join(e(z.strip()) for z in hotel_adresse.split(",") if z.strip()),
        "datum": datum.strftime("%d.%m.%Y"),
        "bestaetigung": e(bestaetigung),
        "rechnungsvermerk": e(vermerk),
        "telefon": e(abs_["telefon"] or abs_["telefon_zentrale"]),
        "zentrale_zeile": f"Tel. {e(abs_['telefon_zentrale'])}<br>" if abs_["telefon_zentrale"] else "",
        "web": e(abs_["web"]),
        "gaeste_html": "<br>".join(e(g) for g in gaeste) or "werden nachgereicht",
        "anreise": e(auftrag["zeitraum"]["anreise"]),
        "abreise": e(auftrag["zeitraum"]["abreise"]),
        "naechte": str(naechte),
        "zimmer": str(zimmer),
        "preis": euro(preis),
        "parkplatz_zeile": e(parkzeile),
        "gesamt": euro(zimmerkosten + parkkosten),
        "ust_id": e(abs_["ust_id"]),
        "rechnung_email": e(abs_["rechnung_email"] or abs_["email"]),
        "marke_html": marke,
        "unterschrift_html": f'<img src="{unterschrift}" alt="Unterschrift">' if unterschrift else "",
        "ohne_unterschrift": ohne_unterschrift,
        "register_html": e(register),
        "ust_zeile": f"USt-IdNr. {e(abs_['ust_id'])}" if abs_["ust_id"] else "",
        "geschaeftsfuehrung": e(abs_["geschaeftsfuehrung"]),
    })
    vorlagen = repowurzel() / "vorlagen" / "kostenuebernahme"
    for feld, datei in (
        ("schrift_light", "RobotoCondensed-Light-latin.woff"),
        ("schrift_bold", "RobotoCondensed-Bold-latin.woff"),
    ):
        schrift = vorlagen / "schrift" / datei
        werte_html[feld] = (
            "data:font/woff;base64," + base64.b64encode(schrift.read_bytes()).decode("ascii")
            if schrift.is_file() else ""
        )
    dokument = ersetze_in_markdown(
        (vorlagen / "dokument.html").read_text(encoding="utf-8"), werte_html
    )

    werte_mail = {
        **sig,
        "referenz_betreff": f"Buchung {bestaetigung} " if bestaetigung else "",
        "anreise": auftrag["zeitraum"]["anreise"],
        "abreise": auftrag["zeitraum"]["abreise"],
        "zimmer": str(zimmer),
        "gaeste_text": ", ".join(gaeste) or "werden nachgereicht",
        "rechnung_email": abs_["rechnung_email"] or abs_["email"],
        "rechnungsvermerk": vermerk,
    }
    betreff, text = mail_zerlegen(
        ersetze_in_markdown((vorlagen / "mail.md").read_text(encoding="utf-8"), werte_mail)
    )

    sauber = "".join(z if z.isalnum() else "_" for z in hotel).strip("_")
    while "__" in sauber:
        sauber = sauber.replace("__", "_")
    dateiname = (
        f"Kostenuebernahme_{auftrag['baustelle'].get('kuerzel') or 'Hotel'}_"
        f"{sauber}_{auftrag['zeitraum'].get('anreise_iso', '')}"
    ).rstrip("_")

    return {
        "betreff": betreff,
        "text": text,
        "html": dokument,
        "dateiname": dateiname,
        "gesamt": round(zimmerkosten + parkkosten, 2),
        "hinweise": hinweise,
    }


# --- PDF ---------------------------------------------------------------------


def _browser(p):
    try:
        return p.chromium.launch()
    except Exception:
        for kandidat in sorted(glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome")):
            try:
                return p.chromium.launch(executable_path=kandidat)
            except Exception:
                continue
        raise


def html_zu_pdf(dokument: str, ziel: Path) -> bool:
    """Druckt das HTML mit Chromium als A4-PDF. False, wenn das nicht geht.

    Ohne Playwright bleibt die HTML-Datei: im Browser öffnen, als PDF drucken.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False
    try:
        with sync_playwright() as p:
            browser = _browser(p)
            seite = browser.new_page()
            seite.set_content(dokument, wait_until="load", timeout=20000)
            # Roboto Condensed kommt aus dem Netz. Ohne Netz greift die
            # Ersatzschrift, das Dokument entsteht trotzdem.
            try:
                seite.evaluate("document.fonts.ready")
            except Exception:
                pass
            seite.pdf(
                path=str(ziel), format="A4", print_background=True,
                margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
            )
            browser.close()
        return True
    except Exception:
        return False
