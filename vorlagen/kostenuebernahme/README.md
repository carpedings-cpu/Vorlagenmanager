# Kostenübernahme fürs Hotel

Nach der Zusage des Hotels geht eine Kostenübernahmeerklärung raus: Das Haus
will wissen, dass die Firma zahlt und nicht der Monteur an der Rezeption.
Das Skript erzeugt sie als PDF im KPC-Design und dazu den Mailtext.

    python3 werkzeuge/hotelsuche.py kostenuebernahme <auftrag.json> \
        --hotel "Hotel Villa Sulmana" --preis 72.50 \
        --bestaetigung "4711" --gaeste "Karl Beispiel" "Emil Beispiel"

`dokument.html` ist die Vorlage für das Schreiben, `mail.md` der Begleittext.
Firmenangaben, Unterschrift und Logo kommen aus `hotels/kriterien.yaml` im
Datenordner unter `absender:`. Logo und Unterschrift sind Bilddateien im
Ordner `hotels/`; fehlen sie, steht eine Wortmarke im Kopf und ein Vermerk,
dass das Schreiben ohne Unterschrift gilt.

Was übernommen wird und was nicht, steht fest in der Vorlage: Zimmer,
Frühstück, Parkplatz und Übernachtungsteuer ja, Minibar und alles Persönliche
nein. Der Satz zur beruflichen Veranlassung ist Absicht: In vielen Städten
befreit er von der Übernachtungsteuer, und die Hotels brauchen ihn schriftlich.
