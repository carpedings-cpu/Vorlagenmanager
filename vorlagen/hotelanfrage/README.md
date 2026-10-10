# Hotelanfrage

Mailtext für die Direktanfrage beim Hotel. Gefüllt wird er aus dem Suchauftrag:

```bash
python3 werkzeuge/hotelsuche.py anfrage <auftrag.json> --hotel "Hotel Amaris"
```

Anders als der übrige Schriftverkehr hängt diese Vorlage nicht an einem Projekt
aus `projekte/`, sondern an einer Baustelle aus `hotels/baustellen.yaml`. Sie
braucht deshalb keine `felder.yaml`, die Platzhalter kommen direkt aus dem
Auftrag.

Sinn der Sache: Direkt beim Hotel buchen statt über das Portal. Das Haus
spart 15 bis 18 Prozent Provision und darf seit 2021 direkt günstiger
anbieten. Die Anfrage nennt deshalb den Portalpreis als Messlatte. Dazu die
Fragen, die in keinem Portal stehen: Frühstückszeit, Parkplatz, Storno. Ab
fünf Nächten zusätzlich die Wochen- oder Monteurpauschale.

Erzeugt wird sie mit `hotelsuche.py anfrage`, Claude legt sie als Entwurf ins
Postfach. Die Kostenübernahme nach der Zusage liegt in
`vorlagen/kostenuebernahme/`.
