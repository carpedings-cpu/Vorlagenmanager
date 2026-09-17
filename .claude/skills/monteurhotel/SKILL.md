---
name: monteurhotel
description: Findet Hotels mit verfügbaren Einzelzimmern in der Nähe einer Baustelle für Monteure - Einzelzimmer mit Dusche/WC, Frühstück, Parkplatz am Haus, gut bewertet. Nutze diesen Skill IMMER wenn Diana eine Übernachtung für Monteure braucht. Auch triggern bei "Hotel für Baustelle X", "Übernachtung für die Monteure", "Zimmer für KW 41", "wo schlafen die Jungs in Bremerhaven", "Monteurzimmer suchen", "Hotel buchen für Montage". Ebenso nutzen, wenn eine neue Baustelle oder ein neuer Monteur in die Stammdaten soll, wenn eine Anfrage ans Hotel geschrieben werden soll, oder wenn eine Buchung in der Historie festgehalten wird.
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
   Hinweis und zählt bei der Bewertung mit der halben Punktzahl. Dazu
   gehört ein kurzer Satz, was man über das Haus sonst weiß: Zimmerart,
   Bad, Parkplatz. Eine schlechte Bewertung fliegt weiter raus.

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

### 2. Live suchen

Dafür das Hotelsuch-Werkzeug der Session nehmen, das nach Koordinaten,
Zeitraum und Ausstattung sucht und die Verfügbarkeit mitliefert (Booking,
sonst Trivago oder Tripadvisor). Den Werkzeugnamen nicht aus diesem Text
übernehmen: Er trägt je nach Session ein anderes Präfix. Erst die verfügbaren
Werkzeuge durchsehen, dann das passende aufrufen. Ist keines da, sagen statt
schätzen; die Verfügbarkeit ist der Kern der Sache.

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

Zu wenige Treffer? Erst den Radius erhöhen, dann den Preis, zuletzt die
Bewertung. Die Bewertung ist das Kriterium, das Diana ausdrücklich gesetzt
hat, also das letzte, das fällt, und ein Absenken wird gesagt.

Antwort als JSON ins Scratchpad schreiben, unverändert.

### 3. Auswerten

```bash
python3 werkzeuge/hotelsuche.py auswerten <auftrag.json> <treffer.json> --ids
```

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

### 6. Buchen oder anfragen

Bis vier Nächte reicht der Buchungslink, Diana bucht selbst.

Ab fünf Nächten setzt der Auftrag `direktanfrage_noetig`. Dann zusätzlich:

```bash
python3 werkzeuge/hotelsuche.py anfrage <auftrag.json> --hotel "<Name>"
```

Der Text fragt Pauschale, Frühstückszeit, Parkplatz, Storno und
Sammelrechnung ab. Vor dem Versand zeigen. Formulierung anpassen mit dem Skill
`diana-formulierungen`, nie ungefragt den Inhalt ändern.

### 7. Festhalten

Nach der Buchung:

```bash
python3 werkzeuge/hotelsuche.py buchen <auftrag.json> --hotel "<Name>" \
    --preis <EUR/Nacht> --gesamt <Angebotssumme> --fazit "<kurz>"
```

Das Fazit ist der eigentliche Wert der Historie. „Parkplatz eng, Frühstück
erst ab 6:30" erspart beim nächsten Einsatz eine halbe Stunde Recherche. Wenn Diana nach dem Einsatz eine Rückmeldung
gibt, nachtragen.

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
mit gleichem Anfangsbuchstaben reichen dafür schon, etwa Ivan Rusev und Ina
Ruseva. Im Zweifel nachfragen, wie die beiden sich in der
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

Er bucht nicht selbst und gibt keine Zahlungsdaten ein. Er liefert geprüfte
Vorschläge mit Link, gebucht wird von Hand. Und er erfindet keine
Verfügbarkeit: Steht im Ergebnis nichts Passendes, wird das gesagt, zusammen
mit dem Kriterium, das man lockern müsste.
