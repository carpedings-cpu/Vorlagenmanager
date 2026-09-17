# Hotelanfrage

Mailtext für die Direktanfrage beim Hotel. Gefüllt wird er aus dem Suchauftrag:

```bash
python3 werkzeuge/hotelsuche.py anfrage <auftrag.json> --hotel "Hotel Amaris"
```

Anders als der übrige Schriftverkehr hängt diese Vorlage nicht an einem Projekt
aus `projekte/`, sondern an einer Baustelle aus `hotels/baustellen.yaml`. Sie
braucht deshalb keine `felder.yaml`, die Platzhalter kommen direkt aus dem
Auftrag.

Sinn der Sache: Ab etwa fünf Nächten liegen Monteur- und Wochenpauschalen
regelmäßig unter dem Portalpreis, und die beiden Fragen, an denen eine Buchung
scheitert, stehen in keinem Portal: Frühstückszeit und Storno.
