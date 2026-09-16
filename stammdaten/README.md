# Stammdaten für die Hotelsuche

Im Repo liegen nur die Vorlagen und die Kriterien. Die ausgefüllten Dateien
liegen im Datenordner unter `hotels/`, zusammen mit der Buchungshistorie:

| Datei | Inhalt |
|---|---|
| `baustellen.yaml` | Je Baustelle Kürzel, Adresse, Koordinaten, Besonderheiten |
| `monteure.yaml` | Kürzel, Name, Fahrzeug samt Höhe, Hinweise |
| `kriterien.yaml` | Nur was von `stammdaten/kriterien.yaml` abweichen soll |
| `buchungen.yaml` | Wächst von selbst: was gebucht wurde und wie es war |
| `hoehen.yaml` | Erfragte Durchfahrtshöhen je Hotel, auch die zu niedrigen |

Angelegt werden sie von `werkzeuge/einrichten.py`. Warum außerhalb des Repos:
Monteurnamen und Fahrzeuge sind Personendaten und gehören nicht in ein
Git-Repository, genauso wenig wie Vertragsdaten.

## Warum Koordinaten und nicht nur die Adresse

Gesucht wird im Radius um einen Punkt. „Hotels in Fulda" liefert auch Häuser,
die 12 km und zwei Ortsdurchfahrten von der Baustelle entfernt liegen. Mit
Koordinaten stimmt die Entfernung, und die Rangfolge stimmt mit.

## Fahrzeughöhe

Der Eintrag `fahrzeughoehe_m` ist kein Beiwerk. Ein Sprinter mit Hochdach misst
rund 2,60 m, ohne Hochdach rund 2,35 m, eine übliche Tiefgarage lässt 2,00 m
durch. Hotels mit reinem Parkhaus werden deshalb aussortiert, sobald ein hohes
Fahrzeug mitfährt.

## Warum die Höhen extra notiert werden

Die Durchfahrtshöhe steht in keiner Ausstattungsliste, auch nicht indirekt.
Ein Berliner Testlauf über vier Hotels mit der Angabe „Privatparkplatz" oder
„Parken vor Ort" ergab auf Nachfrage 2,00 m, 2,00 m, 1,90 m und 1,80 m. Kein
einziges davon nimmt einen Sprinter auf.

Deshalb landet jede erfragte Höhe in `hoehen.yaml`, gerade die zu niedrigen.
Beim nächsten Einsatz sortiert die Suche diese Häuser selbst aus, mit Höhe und
Prüfdatum als Grund, statt sie wieder vorzuschlagen.
