---
name: monteurhotel
description: Findet Hotels mit verfügbaren Einzelzimmern in der Nähe einer Baustelle für Monteure - Einzelzimmer mit Dusche/WC, Frühstück, Parkplatz am Haus, gut bewertet. Nutze diesen Skill IMMER wenn Diana eine Übernachtung für Monteure braucht. Auch triggern bei "Hotel für Baustelle X", "Übernachtung für die Monteure", "Zimmer für KW 41", "wo schlafen die Jungs in Bremerhaven", "Monteurzimmer suchen", "Hotel buchen für Montage". Ebenso nutzen, wenn eine neue Baustelle oder ein neuer Monteur in die Stammdaten soll, wenn eine Anfrage ans Hotel geschrieben werden soll, wenn das Hotel zugesagt hat und eine Kostenübernahme raus muss ("Hotel hat bestätigt", "Go für die Kostenübernahme", "Kostenübernahme fürs Hotel"), oder wenn eine Buchung in der Historie festgehalten wird.
---

# Monteurhotel

Sucht Unterkunft für eine Montage. Stammdaten kommen aus dem Datenordner,
die Verfügbarkeit aus der Live-Suche, die Bewertung der Treffer aus
`werkzeuge/hotelsuche.py`.

## Grundregeln

1. **Verfügbarkeit nie behaupten, immer abfragen.** Ein Hotel, das im letzten
   Monat frei war, ist heute ausgebucht. Jeder Vorschlag stammt aus einer
   Suche für genau diesen Zeitraum, nicht aus der Historie und nicht aus dem
   Gedächtnis.
2. **Parkplatz ja oder nein, mehr nicht.** Ein Haus ohne eigenen Stellplatz
   fällt raus. Ob das Fahrzeug dort auch hineinpasst, prüft Diana selbst beim
   Haus, das ist ausdrücklich nicht Aufgabe der Suche. Keine Durchfahrtshöhen
   sammeln, keine berechnen, keine annehmen.
3. **Entfernung ist Luftlinie.** Das Skript rechnet keine Route. Die Fahrzeit
   ist eine Schätzung und wird auch so benannt. Bei Wasser, Bahntrasse oder
   Werksgelände dazwischen kann die echte Fahrt deutlich länger sein, das bei
   auffälliger Lage erwähnen.
4. **Ein Zimmer pro Mann.** Einzelzimmer mit Dusche und WC im Zimmer, nie
   Doppelzimmer und nie Etagendusche, auch wenn es billiger wäre.
5. **Preis pro Zimmer und Nacht zeigen, nicht die Gesamtsumme.** Die Portale
   nennen den Gesamtpreis für alle Zimmer und alle Nächte. Das ist die Zahl,
   die man falsch vergleicht.
6. **Ohne Bewertung ist kein Ausschlussgrund.** Ein Haus ohne Bewertung ist
   nicht schlecht bewertet, es ist neu. Es steht in der Liste, trägt den
   Hinweis und zählt bei den Punkten so, als erfülle es die Mindestbewertung
   genau: unterstellt wird das geforderte Minimum, nicht mehr. Dazu gehört
   ein kurzer Satz, was man über das Haus sonst weiß: Zimmerart, Bad,
   Parkplatz. Eine schlechte Bewertung fliegt weiter raus.

## Ablauf

### 1. Auftrag bauen

```bash
python3 werkzeuge/hotelsuche.py auftrag <baustelle> <von> <bis> \
    --monteure MK TS --json <scratchpad>/auftrag.json
```

Baustelle über Kürzel, Projektnummer oder Kurzname. Datum als TT.MM.JJJJ.
Kalenderwochen vorher umrechnen und das Ergebnis mitnennen, damit ein
Missverständnis auffällt, bevor gesucht wird.

Die Ausgabe zeigt Zeitraum, Zimmeranzahl, Radius und frühere
Buchungen an dieser Baustelle. Gibt es die Baustelle noch nicht, erst anlegen
(siehe unten), nicht mit einer ungefähren Adresse weitersuchen.

Fehlt der Datenordner, meldet sich das Skript. Dann nicht behelfsmäßig
weiterarbeiten: Die Stammdaten liegen auf Dianas Rechner, eine Cloud-Session
sieht sie nicht.

### 2. Live suchen, und zwar zweigleisig

**Immer Booking und Trivago, nicht nur eines.** Die Werkzeugnamen nicht aus
diesem Text übernehmen, sie tragen je nach Session ein anderes Präfix: erst
die verfügbaren Werkzeuge durchsehen, dann die passenden aufrufen. Beide
Suchen gehen parallel mit denselben Koordinaten und demselben Zeitraum raus.
Ist keine Quelle verfügbar, sagen statt schätzen; die Verfügbarkeit ist der
Kern der Sache.

Warum zwei Quellen, mit Beleg aus Neckarsulm:

| | Booking | Trivago |
|---|---|---|
| Villa Sulmana | ohne Bewertung | 8,1 aus 430 Stimmen |
| Warum ins Hotel | 7,1 aus 125 Stimmen | 8,1 aus 307 Stimmen, 14,60 EUR billiger über Agoda |
| Welcome Hotel | 8,7 aus 1409 | 8,9 aus 2750 |

Trivago zählt die Bewertungen mehrerer Portale zusammen und nennt je Haus das
günstigste. Der Preisvorteil liegt bei wenigen Prozent, die Bewertungslücke
wiegt schwerer: Ein Haus, das bei Booking unbewertet ist oder knapp unter der
Grenze liegt, fällt sonst aus der Liste, obwohl es längst gut bewertet ist.
Tripadvisor taugt als dritte Quelle nur bedingt, es rechnet in Bubbles von 0
bis 5 und lässt sich nicht ohne Umrechnung gegen die 8,0-Grenze stellen.

Parameter aus dem Auftrag:

| Parameter | Wert |
|---|---|
| `coordinates` | `lat`/`lon` der Baustelle, `radius` aus `suche.radius_km` |
| `checkin_date` / `checkout_date` | `zeitraum.anreise_iso` / `abreise_iso` |
| `number_of_adults` | Anzahl Monteure |
| `number_of_rooms` | `zimmer` – gleich der Monteurzahl |
| `meal_plan` | `breakfast_included` |
| `facilities` | `["PARKING"]` |
| `minimum_review_score` | `suche.mindestbewertung`, ganzzahlig |
| `accommodation_types` | `["HOTEL"]`, bei langen Aufenthalten zusätzlich `APARTMENT` |
| `cancellation_type` | `free_cancellation`, wenn im Auftrag gesetzt |
| `currency` | `EUR`, `user_country_code` `de`, `user_locale` `de` |

**Das Preislimit nicht an die Suche geben.** Kein `price.maximum`, auch wenn
das Feld "pro Nacht" verspricht. Booking rechnet es gegen den Gesamtpreis für
alle Zimmer und alle Nächte, und damit filtert es bei zwei Zimmern doppelt so
scharf wie gewollt. In Neckarsulm lieferte `price.maximum: 100` keinen einzigen
Treffer, obwohl vier Häuser zwischen 67 und 99 EUR je Zimmer und Nacht frei
waren. Das Limit wendet die Auswertung an, und die rechnet den Preis vorher
auf Zimmer und Nacht herunter.

Zu wenige Treffer? Erst den Radius erhöhen, dann den Preis, zuletzt die
Bewertung. Die Bewertung ist das Kriterium, das Diana ausdrücklich gesetzt
hat, also das letzte, das fällt, und ein Absenken wird gesagt.

Trivago nimmt eigene Parameter: `arrival`/`departure` statt der Datumsfelder,
`rooms` und `adults`, `country: DE`, `currency: EUR`, `language: DE_DE`, dazu
`filters` mit `breakfastIncluded` und `parking` und `review_rating` mit
`rating80`. Liefert es mit Frühstücksfilter zu wenig, einmal ohne nachfassen:
Trivago kennt den Haken nicht bei jedem Haus, auch wenn Frühstück dabei ist.

Beide Antworten als JSON ins Scratchpad schreiben, unverändert und in
getrennte Dateien.

### 3. Auswerten

```bash
python3 werkzeuge/hotelsuche.py auswerten <auftrag.json> \
    <booking.json> <trivago.json> --ids
```

Das Format erkennt das Skript selbst, Trivago-Treffer rechnet es um. Bei mehr
als einer Datei fasst es dasselbe Haus zu einer Zeile zusammen: günstigerer
Preis, Bewertung aus der Quelle mit den meisten Stimmen, nicht mit der besten
Note. Die Tabelle trägt dann eine Spalte, über welches Portal zu buchen ist,
und nennt darunter den Preisvorteil. Steht dort ein anderes Portal als
Booking, gehört der Hinweis in den Vorschlag: Diana bucht dort, nicht bei
Booking.

Liefert die Rangfolge aus Entfernung, Preis, Bewertung und Parkplatz, dazu
die Aussortierten mit Grund. Die Tabelle nicht neu erfinden, sondern
übernehmen: Die Zahlen darin sind gerechnet, nicht geschätzt.

Darunter steht, was der Einsatz je Vorschlag wirklich kostet, Zimmer plus
Anfahrt. Platz 1 der Rangfolge ist nicht immer die günstigste Summe: Nähe und
Preis gehen getrennt in die Punkte ein, und zwanzig Kilometer mehr kosten über
drei Nächte weniger Sprit, als ein teureres Haus an Zimmerpreis frisst. Liegt
ein hinterer Platz unterm Strich vorn, sagt die Ausgabe das, und du sagst es
Diana auch, statt stumpf Platz 1 zu empfehlen.

### 4. Offene Punkte klären

Für jeden Treffer, den du vorschlägst, und nicht nur für die mit 🔍:
das Detailwerkzeug derselben Hotelquelle, das Rückfragen zu einzelnen Häusern
beantwortet, mit den Hotel-IDs aus `--ids`. Sinnvolle Fragen:

- ab wann Frühstück serviert wird, werktags
- was der Parkplatz pro Nacht kostet, falls nicht inklusive
- ob es echte Einzelzimmer gibt oder nur Doppelzimmer zur Einzelnutzung

Antworten ohne Beleg nicht als gesichert ausgeben. Was das Portal nicht
hergibt, kommt in die Anfragemail an Punkt 2 und 3.

**Vorsicht bei weichen Formulierungen.** Das Detailwerkzeug antwortet auch
dann, wenn es die Sache nicht sicher weiß: „is likely an open outdoor lot",
„suggests there is no height barrier". Das ist eine Vermutung aus der
Ausstattungsliste, kein erfragter Wert, und darf nicht als gesichert in den
Vorschlag.

### 5. Vorschlagen

Drei Treffer, jeweils zwei Sätze: warum dieser, was daran unklar ist. Dazu
die Gesamtkosten für den Einsatz und der Buchungslink. Kein Hotel vorschlagen,
dessen Parkplatzlage ungeklärt ist, ohne das dazuzuschreiben.

War an dieser Baustelle schon etwas gebucht und ist es wieder frei, gehört das
an den Anfang: bekannter Ablauf, bekannte Anfahrt, keine Überraschung.

### 6. Direkt beim Hotel anfragen, als Mailentwurf

**Direkt buchen ist der Standard.** Portale nehmen dem Hotel 15 bis 18 Prozent
Provision ab, und seit dem BGH-Urteil von 2021 darf es direkt günstiger
anbieten. Die Anfrage nennt den Portalpreis, damit das Haus weiß, was es
schlagen muss.

Ausnahme: Zeigt der Auftrag `Buchung: Portal oder Anruf`, ist die Anreise zu
nah für eine Mail (Grenze `direktbuchung_mindestvorlauf_tage`). Dann Link und
Telefonnummer des Hauses liefern, keinen Entwurf.

**Sobald du eine Anfrage empfiehlst, legst du den Entwurf an.** Nicht erst
fragen, ob Diana einen will. Für die Empfehlung, bei knappem Markt zusätzlich
für die zweite Wahl; dann dazusagen, dass einem der beiden abgesagt werden
muss.

1. **Mailadresse des Hotels** aus dem Impressum der Hotelwebsite holen. Das
   Impressum ist in Deutschland Pflicht und nennt eine Adresse, die jemand
   liest. Keine Adresse raten, keine aus einem Portal übernehmen, das sind
   Weiterleitungen. Findet sich keine, Entwurf ohne Empfänger und das sagen.
   Telefonnummer gleich mitnehmen, für den Fall, dass die Antwort ausbleibt.
2. **Text erzeugen**, mit dem günstigsten Portalpreis je Zimmer und Nacht für
   genau dieses Haus aus der Auswertung:

   ```bash
   python3 werkzeuge/hotelsuche.py anfrage <auftrag.json> \
       --vergleichspreis <EUR> --an <hotel@...> --hotel "<Name>" \
       --json <scratchpad>/anfrage_<kurz>.json
   ```

3. **Entwurf anlegen** mit dem Gmail-Werkzeug der Session (`create_draft`):
   Empfänger, Betreff und Text aus der JSON-Datei, Text als `body`, ohne
   Markdown. Ist das verbundene Postfach nicht die Firmenadresse aus
   `absender.email`, die Firmenadresse in CC: Dann liegt die Korrespondenz
   auch im Firmenpostfach, und eine Antwort an alle kommt dort an.
4. **Diana den Link zum Entwurf geben**, dazu was offen ist (Empfänger nicht
   gefunden, Vergleichspreis fehlt).

**Niemals abschicken.** Es gibt keinen Fall, in dem du eine Mail ans Hotel
selbst versendest. Der Entwurf ist die Lieferung, Diana liest gegen und
drückt auf Senden. Formulierung ändern nur auf Wunsch, mit dem Skill
`diana-formulierungen`, den Inhalt nie ungefragt.

Mitfahrer im selben Fahrzeug: Den Auftrag mit `--fahrzeuge` bauen. Zwei Mann
in einem Sprinter brauchen einen Stellplatz, die Mail fragt sonst nach zwei.
Die Fahrzeugart steht nicht in der Mail, die prüft Diana selbst.

### 7. Kostenübernahme, erst nach Zusage und Go

Die Kostenübernahme ist eine Zahlungszusage der Firma. Sie entsteht erst,
wenn zwei Dinge vorliegen: **die Zusage des Hotels** mit freien Zimmern und
Preis, und **Dianas Go**. Fehlt eines, nichts anlegen.

1. **Antwort des Hotels lesen** im Postfach: bestätigter Preis je Zimmer und
   Nacht, Buchungsnummer, Anschrift aus der Signatur, Parkgebühr falls extra.
   Der Preis aus der Suche zählt nicht mehr, nur der bestätigte.
2. **Gäste**: Namen aus dem Auftrag. Fehlt ein Nachname, fragen. Nie einen
   Platzhalternamen in ein echtes Dokument schreiben.
3. **Dokument erzeugen:**

   ```bash
   python3 werkzeuge/hotelsuche.py kostenuebernahme <auftrag.json> \
       --hotel "<Name>" --preis <bestätigt> --bestaetigung "<Nr>" \
       --hotel-adresse "<Straße>, <PLZ Ort>" --gaeste "<Name>" "<Name>" \
       --an <hotel@...> --json <scratchpad>/kosten_<kurz>.json
   ```

   Ergebnis: die Erklärung als formatierter Mailtext (`html` in der JSON),
   dazu ein einseitiges PDF im KPC-Design unter `hotels/post/`. Hinweise auf
   stderr (fehlende Pflichtangaben nach § 35a GmbHG, Gästezahl passt nicht
   zur Zimmerzahl) gehören in die Antwort an Diana, nicht unter den Tisch.
4. **Prüfen, bevor es ins Postfach geht**: Summe gleich Preis mal Zimmer mal
   Nächte, Namen richtig geschrieben, Buchungsnummer wie in der Hotelmail.
5. **Antwortentwurf im selben Verlauf** anlegen: `create_draft` mit
   `replyToMessageId` auf die Nachricht des Hotels, Betreff aus der JSON,
   den Mailtext als `htmlBody`. **Das PDF nicht anhängen.** Das Werkzeug
   nimmt Anhänge nur als base64 im Aufruf; bei 30 KB sind das über 40.000
   Zeichen, ein einziger Übertragungsfehler zerstört das Dokument, und
   prüfen lässt sich der Anhang danach nicht. Die Erklärung steht vollständig
   im Mailtext, das ist Textform und genügt. Das PDF bekommt Diana als Datei,
   falls ein Hotel ausdrücklich eins verlangt.
6. Nach dem Anlegen den Entwurf mit `get_draft` zurücklesen und Betrag,
   Namen und Zeitraum gegen die JSON prüfen. Wieder: nicht abschicken.

**Absender-Postfach.** Entwürfe landen in dem Postfach, das in der Session
verbunden ist. Ist das eine private Adresse und nicht `absender.email`, geht
die Kostenübernahme von dort raus, und ein Hotel kann eine Zahlungszusage
von einer Privatadresse zu Recht ablehnen. Das bei jeder Kostenübernahme
dazusagen, solange es so ist.

### 8. Festhalten

Nach der Buchung:

```bash
python3 werkzeuge/hotelsuche.py buchen <auftrag.json> --hotel "<Name>" \
    --preis <EUR/Nacht> --gesamt <Angebotssumme> --fazit "<kurz>"
```

Das Fazit ist der eigentliche Wert der Historie. „Parkplatz eng, Frühstück
erst ab 6:30" erspart beim nächsten Einsatz eine halbe Stunde Recherche. Wenn
Diana nach dem Einsatz eine Rückmeldung gibt, nachtragen. Hat das Hotel
direkt einen Preis unter dem Portal gemacht, gehört auch das ins Fazit: Beim
nächsten Mal weiß man, dass es sich lohnt zu fragen.

## Neue Baustelle anlegen

Adresse von Diana, Koordinaten ergänzt du. In `hotels/baustellen.yaml`:

```yaml
  - kuerzel: XYZ
    projektnummer: "2451"
    kurzname: Kurzer Name
    strasse: Musterstraße 1
    plz: "12345"
    ort: Musterstadt
    koordinaten: {lat: 50.5558, lon: 9.6808}
    max_entfernung_km: 15
    hinweis: ""
```

Koordinaten auf vier Nachkommastellen, das sind rund 10 m. Bei großen
Werksgeländen den Punkt aufs Tor legen, an dem die Monteure morgens
reinfahren, nicht auf die Mitte des Grundstücks: gesucht wird um diesen Punkt.

Wenn du die Koordinaten nicht sicher weißt, sag das und lass sie nachreichen.
Eine falsche Koordinate verschiebt die gesamte Suche, ohne dass es auffällt.

Neue Monteure analog in `hotels/monteure.yaml`.

**Kürzel müssen eindeutig sein.** Das Skript bricht sonst ab, und das ist
Absicht: Zwei Leute mit demselben Kürzel würden beim Nachschlagen still
denselben Eintrag liefern, und im Hotel läge der falsche Mann. Zwei Nachnamen
mit gleichem Anfangsbuchstaben reichen dafür schon, etwa Ivo Reiter und Iris
Reiter. Im Zweifel nachfragen, wie die beiden sich in der
Leistungsfeststellungs-App eintragen, und danach richten.

Anlegen kann Diana Monteure auch selbst im Cockpit unter Stammdaten. Die
liegen dann im Browser; der Exportknopf dort liefert den Inhalt für
`monteure.yaml`. Spricht sie von jemandem, den das Skript nicht kennt, ist
vermutlich der Export noch nicht gelaufen.

## Heimfahrt statt Hotel

Liegt die Baustelle in Reichweite des Betriebssitzes, hängt die Auswertung von
selbst eine Gegenrechnung an: Zimmer, Diesel und Verpflegungspauschale auf
beiden Seiten, dazu die Fahrzeit. Die Grenze steht in `kriterien.yaml` unter
`heimfahrt_pruefen_bis_km`.

Zwei Dinge dabei nicht übersehen. Der reine Kostenvergleich sagt auch bei
500 km noch "fahr heim", weil Diesel billiger ist als ein Zimmer - deshalb
prüft die Rechnung die tägliche Fahrzeit je Mann gegen
`fahrzeit_zumutbar_h` und sagt es, wenn das nicht mehr geht. Und die Fahrzeit
ist ausgewiesen, aber nicht als Kosten eingerechnet: Ob sie als Arbeitszeit
zählt, ist eine betriebliche Frage, keine Rechenregel. Wenn Diana danach
fragt, nicht selbst entscheiden.

Der Dieselpreis in `kriterien.yaml` ist ein Stichtagswert und schwankt stark.
Kommt eine Rechnung auf den Cent an, vorher nachsehen, ob er noch stimmt.

## Cockpit

Für den Klickweg gibt es eine erzeugte HTML-Oberfläche:

```bash
python3 werkzeuge/cockpit.py
```

Sie landet im Datenordner unter `hotels/cockpit.html` und trägt die Stammdaten
fest eingebaut. **Nach jeder Änderung an Baustellen, Monteuren oder Buchungen
neu erzeugen**, sonst zeigt sie einen alten Stand. Kommt Diana mit einem
Auftragstext aus dem Cockpit, ist das derselbe Ablauf wie oben ab Schritt 2:
Der Text enthält Koordinaten, Radius und Zimmerzahl schon fertig.

Trägt sie im Cockpit Buchungen oder Monteure ein, liegen die zunächst nur im
Browser. Die Exportknöpfe schreiben die YAML-Dateien, die in den Datenordner
gehören. Wenn sie also von Einträgen spricht, die im Skript nicht auftauchen:
danach fragen, ob der Export schon gelaufen ist.

## Kriterien ändern

`stammdaten/kriterien.yaml` ist die Vorgabe im Repo. Eigene Werte kommen in
`hotels/kriterien.yaml` im Datenordner und gelten vorrangig, damit Änderungen
ein Update überstehen. Einzelne Baustellen dürfen `max_entfernung_km`
überschreiben: In Berlin sind 8 km viel, in der Rhön sind 25 km normal.

## Was dieser Skill nicht macht

Er bucht nicht selbst, gibt keine Zahlungsdaten ein und schickt keine Mail
ab. Er liefert geprüfte Vorschläge, Anfragen und Kostenübernahmen als
Entwürfe im Postfach, abgeschickt wird von Hand. Und er erfindet keine
Verfügbarkeit: Steht im Ergebnis nichts Passendes, wird das gesagt, zusammen
mit dem Kriterium, das man lockern müsste.
