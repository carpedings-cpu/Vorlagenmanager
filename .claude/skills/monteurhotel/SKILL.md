---
name: monteurhotel
description: Findet Hotels mit verfügbaren Einzelzimmern in der Nähe einer Baustelle für Monteure - Einzelzimmer mit Dusche/WC, Frühstück, Parkplatz für den Sprinter, gut bewertet. Nutze diesen Skill IMMER wenn Diana eine Übernachtung für Monteure braucht. Auch triggern bei "Hotel für Baustelle X", "Übernachtung für die Monteure", "Zimmer für KW 41", "wo schlafen die Jungs in Bremerhaven", "Monteurzimmer suchen", "Hotel buchen für Montage". Ebenso nutzen, wenn eine neue Baustelle oder ein neuer Monteur in die Stammdaten soll, wenn eine Anfrage ans Hotel geschrieben werden soll, oder wenn eine Buchung in der Historie festgehalten wird.
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
2. **Parkplatz ist ein hartes Kriterium, kein Komfort.** Der Sprinter muss
   nachts stehen können. Die Durchfahrtshöhe steht in **keiner**
   Ausstattungsliste, auch nicht indirekt: Das Limehome Berlin führt
   „Privatparkplatz, Parken vor Ort" ohne jede Erwähnung eines Parkhauses
   und hat trotzdem 2,00 m Schranke. Deshalb die Höhe bei **jedem** Haus
   erfragen, das du vorschlägst, auch bei grünem Häkchen. Das Häkchen heißt
   nur, dass ein Stellplatz existiert, nicht dass er hoch genug ist. Steht die
   Höhe schon in `hotels/hoehen.yaml`, gilt sie und es wird nicht neu gefragt.
3. **Entfernung ist Luftlinie.** Das Skript rechnet keine Route. Die Fahrzeit
   ist eine Schätzung und wird auch so benannt. Bei Wasser, Bahntrasse oder
   Werksgelände dazwischen kann die echte Fahrt deutlich länger sein, das bei
   auffälliger Lage erwähnen.
4. **Ein Zimmer pro Mann.** Einzelzimmer mit Dusche und WC im Zimmer, nie
   Doppelzimmer und nie Etagendusche, auch wenn es billiger wäre.
5. **Preis pro Zimmer und Nacht zeigen, nicht die Gesamtsumme.** Die Portale
   nennen den Gesamtpreis für alle Zimmer und alle Nächte. Das ist die Zahl,
   die man falsch vergleicht.

## Ablauf

### 1. Auftrag bauen

```bash
python3 werkzeuge/hotelsuche.py auftrag <baustelle> <von> <bis> \
    --monteure MK TS --json <scratchpad>/auftrag.json
```

Baustelle über Kürzel, Projektnummer oder Kurzname. Datum als TT.MM.JJJJ.
Kalenderwochen vorher umrechnen und das Ergebnis mitnennen, damit ein
Missverständnis auffällt, bevor gesucht wird.

Die Ausgabe zeigt Zeitraum, Zimmeranzahl, Radius, Fahrzeughöhe und frühere
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

### 4. Offene Punkte klären

Für jeden Treffer, den du vorschlägst, und nicht nur für die mit 🔍:
das Detailwerkzeug derselben Hotelquelle, das Rückfragen zu einzelnen Häusern
beantwortet, mit den Hotel-IDs aus `--ids`. Sinnvolle Fragen:

- Durchfahrtshöhe des Stellplatzes, immer, egal was die Ausstattung sagt
- ab wann Frühstück serviert wird, werktags
- was der Parkplatz pro Nacht kostet, falls nicht inklusive
- ob es echte Einzelzimmer gibt oder nur Doppelzimmer zur Einzelnutzung

Antworten ohne Beleg nicht als gesichert ausgeben. Was das Portal nicht
hergibt, kommt in die Anfragemail an Punkt 2 und 3.

**Jede erfragte Durchfahrtshöhe sofort festhalten**, auch und gerade die zu
niedrigen:

```bash
python3 werkzeuge/hotelsuche.py hoehe <hotel-id> <meter> --name "<Hotel>"
```

Das Verzeichnis liegt in `hotels/hoehen.yaml` und wird bei jeder Auswertung
gelesen. Ein eingetragenes Haus wird künftig selbst aussortiert, mit Höhe und
Prüfdatum als Grund, statt wieder vorgeschlagen und wieder abgefragt zu
werden. Ein Parkhaus wird nicht höher, der Wert hält.

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

Der Text fragt Pauschale, Frühstückszeit, Durchfahrtshöhe, Storno und
Sammelrechnung ab. Vor dem Versand zeigen. Formulierung anpassen mit dem Skill
`diana-formulierungen`, nie ungefragt den Inhalt ändern.

### 7. Festhalten

Nach der Buchung:

```bash
python3 werkzeuge/hotelsuche.py buchen <auftrag.json> --hotel "<Name>" \
    --preis <EUR/Nacht> --gesamt <Angebotssumme> --fazit "<kurz>"
```

Das Fazit ist der eigentliche Wert der Historie. Die bestätigte
Durchfahrtshöhe gehört immer hinein, weil sie sonst nirgends steht:
„Stellplatz im Hof, Durchfahrt 3,20 m, Frühstück ab 6:00" erspart beim
nächsten Einsatz eine halbe Stunde Recherche und einen Fehlgriff. Wenn Diana nach dem Einsatz eine Rückmeldung
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

Neue Monteure analog in `hotels/monteure.yaml`, mit `fahrzeughoehe_m`. Der Wert
entscheidet, ob Parkhäuser ausgeschlossen werden: Sprinter mit Hochdach rund
2,60 m, Vito rund 1,95 m.

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
