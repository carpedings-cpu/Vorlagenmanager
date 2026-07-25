# Vorlagen anlegen

Ein Ordner je Schreiben. Der Ordnername ist gleichzeitig der Aufruf­name.

```
vorlagen/bedenkenanmeldung/
  vorlage.docx    ← das bestehende Schreiben, variable Stellen als {{platzhalter}}
  felder.yaml     ← woher jeder Platzhalter seinen Wert bekommt
  mail.md         ← Betreff und Text für den Mail-Entwurf (optional)
```

## 1. vorlage.docx

Nimm ein echtes Schreiben, das du schon einmal rausgeschickt hast. Briefkopf,
Schriftart, Fußzeile, alles bleibt – es wird nur ersetzt, nicht neu gesetzt.
Ersetze die Stellen, die je Projekt oder Fall wechseln, durch `{{key}}`:

> Sehr geehrte Damen und Herren,
> hiermit melden wir Bedenken gegen die Ausführung der Leistung
> **{{betroffene_leistung}}** im Bauvorhaben **{{bauvorhaben}}** an.

Platzhalter funktionieren auch in Kopf- und Fußzeile und in Tabellen –
also auch im Briefkopf für Aktenzeichen, Datum und Anschrift.

Ein Platzhalter besteht aus Kleinbuchstaben, Ziffern und Unterstrich:
`{{ag_firma}}`, `{{frist_1}}`. Keine Leerzeichen, keine Umlaute.

## 2. felder.yaml

Hier steht, woher jeder Wert kommt. Das ist der Teil, der die Abfrage kurz hält.

```yaml
name: Bedenkenanmeldung nach § 4 Abs. 3 VOB/B
kuerzel: BED
dokumententyp: Bedenkenanmeldung   # für die Benennung nach VA 1.3
datei: vorlage.docx
mail: mail.md

felder:
  - key: bauvorhaben
    label: Bauvorhaben
    quelle: projekt
    pfad: bauvorhaben
```

### Die fünf Quellen

| `quelle` | Bedeutung | Wird gefragt? |
|---|---|---|
| `projekt` | Steht in `projekt.yaml`, Feld über `pfad` | nein |
| `vertrag` | Wird in `vertrag/` gesucht, mit Fundstelle belegt | nur zur Bestätigung |
| `abfrage` | Fallspezifisch, kommt von dir | ja |
| `berechnet` | Aus anderen Feldern abgeleitet, z. B. Fristen | nein |
| `fest` | Immer derselbe Text, steht als `wert` dabei | nein |

**Faustregel: so viel wie möglich auf `projekt`.** Alles, was sich innerhalb
eines Projekts nicht ändert – auch Vertragsdatum, Auftragssumme oder
Ausführungsfristen – gehört in die `projekt.yaml` und wird dort einmal gepflegt.
`quelle: vertrag` ist nur für Werte gedacht, die von Fall zu Fall aus einem
konkreten Dokument kommen. Je mehr auf `projekt` steht, desto kürzer die Abfrage.

### Alle Schlüssel

```yaml
- key: vertragsdatum          # Pflicht – der Platzhaltername ohne {{ }}
  label: Datum des Vertrags   # Pflicht – Klartext für Abfrage und Übersicht
  quelle: vertrag             # Pflicht – siehe Tabelle oben
  typ: datum                  # text | datum | betrag | zahl | mehrzeilig
  pflicht: true               # false = darf leer bleiben

  # nur bei quelle: projekt
  pfad: auftraggeber.firma    # Pfad in projekt.yaml, Punkt für Verschachtelung

  # nur bei quelle: vertrag
  suchhinweis: "Datum der Auftragsbestätigung bzw. Vertragsurkunde"
  dateien: [auftragsbestaetigung, vertrag]   # optional, engt die Suche ein

  # nur bei quelle: abfrage
  frage: "Welche Position ist betroffen?"
  beispiel: "Pos. 3.14 – Estrich EG"
  auswahl: [Lieferung, Montage, Inbetriebnahme]   # optional, dann Auswahlliste

  # nur bei quelle: berechnet
  formel: "heute + 10 werktage"

  # nur bei quelle: fest
  wert: "Wir behalten uns Mehrkosten ausdrücklich vor."
```

### Formeln

| Formel | Ergebnis |
|---|---|
| `heute` | heutiges Datum |
| `heute + 10 werktage` | Datum in 10 Werktagen (Sa/So ausgenommen) |
| `heute + 14 tage` | Kalendertage |
| `<feld> + 12 werktage` | ausgehend von einem anderen Datumsfeld |

Feiertage sind bewusst nicht eingerechnet – bei einer Frist, an der Geld hängt,
wird das Ergebnis ohnehin vorgelegt, bevor es im Schreiben landet.

## 3. mail.md

Betreff und Mailtext, gleiche Platzhalter. Wird als Entwurf mit ausgegeben.

```markdown
---
betreff: "{{projektnummer}} {{bauvorhaben}} – Bedenkenanmeldung {{betroffene_leistung}}"
---

Sehr geehrte Damen und Herren,

anbei erhalten Sie unsere Bedenkenanmeldung zur o. g. Leistung.
Wir bitten um Rückmeldung bis zum {{fristende}}.
```

## Prüfen

```bash
python3 werkzeuge/pruefe_vorlage.py vorlagen/bedenkenanmeldung
```
