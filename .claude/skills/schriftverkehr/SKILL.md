---
name: schriftverkehr
description: Erzeugt wiederkehrenden Projektschriftverkehr aus Vorlagen mit Platzhaltern - Bedenkenanmeldung, Behinderungsanzeige, Nachtragsankündigung, Mahnung, Abnahmeaufforderung und Ähnliches. Nutze diesen Skill IMMER wenn Diana ein Schreiben zu einem Projekt braucht und dafür eine Vorlage in vorlagen/ existiert. Auch triggern bei "Bedenkenanmeldung für Projekt X", "Behinderungsanzeige schreiben", "Schreiben aus Vorlage", "Nachtrag ankündigen", "Vorlage ausfüllen", "Schriftverkehr generieren". Ebenso nutzen, wenn eine neue Vorlage angelegt oder eine bestehende geändert werden soll, oder wenn ein neues Projekt aus einer Auftragsbestätigung angelegt wird.
---

# Schriftverkehr-Generator

Füllt eine Vorlage mit Platzhaltern zu einem fertigen Schreiben plus Mail-Entwurf.
Der Generator **füllt aus, er dichtet nicht**: Formulierungen kommen aus der
Vorlage, Werte aus Projektdaten, Vertragsdateien oder der Abfrage.

## Grundregeln

1. **Nie raten bei scharfen Werten.** Fristen, Daten, Beträge, Vertragsnummern,
   Paragrafen: entweder mit Fundstelle belegt (Datei und Seite) oder gefragt.
   Ein falsches Vertragsdatum in einer Bedenkenanmeldung kostet Geld.
2. **Erst zeigen, dann schreiben.** Vor der Generierung immer die Ausfüll-Übersicht.
3. **Gebündelt fragen.** Alle offenen Felder in einer Nachricht, nicht einzeln.
4. **Keine neuen Textbausteine erfinden.** Fehlt in der Vorlage ein Absatz,
   sag das – ändere nicht heimlich den Text des Schreibens.

## Ablauf

### 1. Projekt und Vorlage bestimmen

Vorlagen liegen in `vorlagen/<name>/`, Projekte in `projekte/<nummer>_<kurzname>/`.
Bei Unklarheit die vorhandenen auflisten und fragen.

Fehlt das Projekt: anbieten, es aus der Auftragsbestätigung anzulegen
(siehe „Neues Projekt" unten). Nicht mit einem halb erfundenen Projekt weiterarbeiten.

### 2. Offene Felder ermitteln

```bash
python3 werkzeuge/fuelle.py vorlagen/<vorlage> projekte/<projekt> --offen
```

Ausgegeben wird, was weder aus `projekt.yaml` noch aus Festwerten oder Formeln
kommt: die Felder mit `quelle: vertrag` und `quelle: abfrage`.

### 3. Vertragsfelder belegen

Für jedes Feld mit `quelle: vertrag`: in `projekte/<projekt>/vertrag/` suchen,
geleitet vom `suchhinweis`. Gefundenen Wert **mit Fundstelle** notieren –
Dateiname und Seite. Nicht gefunden heißt nicht gefunden; dann wandert das Feld
in die Abfrage.

### 4. Ausfüll-Übersicht zeigen

| Feld | Wert | Quelle | Status |
|---|---|---|---|
| Auftraggeber | Musterbau GmbH | projekt.yaml | ✅ |
| Vertragsdatum | 14.03.2026 | AB_2451.pdf, S. 1 | 🔍 bitte prüfen |
| Betroffene Leistung | – | – | ❓ offen |

- ✅ aus den Stammdaten, Festwert oder Formel
- 🔍 aus einer Vertragsdatei gelesen, Fundstelle dabei, kurz gegenlesen
- ❓ offen, wird gefragt

### 5. Abfragen

Alle ❓-Felder in einer Nachricht, nummeriert, mit `frage` und `beispiel` aus
der `felder.yaml`. Felder mit `auswahl` über AskUserQuestion.

Bei `typ: mehrzeilig` gibt Diana den Sachverhalt in Stichworten – dann mit dem
Skill `diana-formulierungen` ausformulieren und **den Vorschlag zeigen**, bevor
er ins Schreiben geht. Inhalt kommt von ihr, Formulierung von dir.

Für Bedenken- und Behinderungssachverhalte gilt: Tatsachen, keine Wertung,
keine Schuldzuweisung. Was ist, nicht wer schuld ist.

### 6. Generieren

Werte als JSON ins Scratchpad schreiben, dann:

```bash
python3 werkzeuge/fuelle.py vorlagen/<vorlage> projekte/<projekt> \
    --werte <scratchpad>/werte.json --stichwort "<Kurzbezeichnung>"
```

Das Skript bricht ab, solange Pflichtfelder leer sind. Das ist Absicht –
`--erzwingen` nur, wenn Diana ausdrücklich einen Entwurf mit Lücken will.

Ergebnis landet in `ausgang/<projekt>/`, benannt
`JJJJ-MM-TT_<Projektnummer>_<Dokumententyp>_<Stichwort>`. Weicht die
Verfahrensanweisung davon ab, gilt der Skill `kpc-dokumentenbenennung`.

### 7. Übergeben

Beide Dateien mit SendUserFile schicken: das Schreiben und den Mail-Entwurf.
Dazu in zwei Sätzen, was noch zu prüfen ist – insbesondere die 🔍-Felder.

`ausgang/` wird nicht ins Git eingecheckt. Die fertigen Schreiben gehören in
eure Ablage, nicht in die Repo-Historie.

## Neue Vorlage anlegen

Diana lädt ein bestehendes Schreiben als DOCX hoch. Dann:

1. Ordner `vorlagen/<name>/` anlegen, Datei als `vorlage.docx` hineinlegen.
2. Text lesen und die variablen Stellen vorschlagen – **als Liste zur Bestätigung**,
   nicht einfach ersetzen. Fixer Text bleibt fix.
3. Nach Freigabe die Platzhalter setzen und `felder.yaml` schreiben. Jedes Feld
   bekommt die Quelle, die den geringsten Aufwand macht: was in `projekt.yaml`
   steht, wird nie gefragt.
4. Optionale Abschnitte in `{{?feld}} … {{/feld}}` klammern, damit die Überschrift
   mitverschwindet, wenn das Feld leer bleibt.
5. `mail.md` dazu.
6. Prüfen:
   ```bash
   python3 werkzeuge/pruefe_vorlage.py vorlagen/<name>
   ```
7. Einmal probeweise gegen ein echtes Projekt generieren und das Ergebnis zeigen.

Details zum Schema: `vorlagen/README.md`.

## Neues Projekt anlegen

Aus der Auftragsbestätigung. `projekte/_vorlage_projekt.yaml` kopieren, aus dem
Dokument füllen, alles Unsichere leer lassen statt zu raten. Danach die
ausgefüllte Datei zeigen und um Korrektur bitten – Stammdaten wandern in jedes
Schreiben, ein Fehler hier vervielfältigt sich.

Nur Dateien nach `vertrag/`, die tatsächlich Werte liefern: Auftragsbestätigung,
LV, Bauzeitenplan, besondere Vertragsbedingungen, Nachträge. Keine Fotos, Pläne
oder Protokolle.

## Voraussetzung

`python-docx` muss installiert sein:

```bash
pip install -r requirements.txt
```
