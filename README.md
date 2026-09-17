# Vorlagenmanager – Generator für wiederkehrenden Schriftverkehr

Erzeugt aus einer Vorlage mit Platzhaltern und den Projektdaten ein
fertiges Schreiben (DOCX) plus passenden Mail-Entwurf.

Der Kern der Idee: **Jeder Platzhalter weiß, woher sein Wert kommt.**
Dadurch wird vor der Generierung nur das gefragt, was wirklich fallspezifisch
ist – alles andere kommt aus den Projektstammdaten oder den Vertragsdateien.

## Programm und Daten sind getrennt

Vertragsdaten gehören nicht in ein Git-Repository. Deshalb liegt hier nur das
Programm; die Projektdaten liegen in einem Ordner auf dem eigenen Rechner.

**Im Repo:**

| Ordner | Inhalt |
|---|---|
| `vorlagen/` | Je Schreiben ein Ordner: die DOCX-Vorlage, `felder.yaml`, `mail.md` |
| `werkzeuge/` | Skripte zum Einrichten, Prüfen, Ausfüllen und Hotelsuchen |
| `stammdaten/` | Suchkriterien und Vorlagen für Baustellen und Monteure |
| `tests/` | Regressionstests der Platzhalterersetzung und der Hotelsuche |
| `.claude/skills/schriftverkehr/` | Der Skill, der die Generierung steuert |
| `.claude/skills/monteurhotel/` | Der Skill für die Hotelsuche |

**Im Datenordner, z. B. `~/Desktop/Vorlagenmanager-Daten/`:**

| Ordner | Inhalt |
|---|---|
| `projekte/` | Je Projekt: `projekt.yaml` (Stammdaten) + `vertrag/` (bei Bedarf) |
| `ausgang/` | Die generierten Schreiben, nach Projekt sortiert |
| `hotels/` | `baustellen.yaml`, `monteure.yaml`, `buchungen.yaml` |

Einmalig einrichten:

```bash
python3 werkzeuge/einrichten.py ~/Desktop/Vorlagenmanager-Daten
```

Der Pfad landet in `.datenpfad` und wird nicht eingecheckt. Alternativ die
Umgebungsvariable `VORLAGENMANAGER_DATEN` setzen. Ohne beides wird im Repo
gearbeitet – das ist nur für das Beispielprojekt gedacht.

Damit läuft der Generator **auf deinem Rechner**, nicht in der Cloud: über die
Claude-Code-Desktop-App oder das CLI, geöffnet auf diesem Repo. Eine Session im
Browser sieht deinen Desktop nicht.

## Ablauf

1. **Anstoßen** – „Bedenkenanmeldung für Klinikum XY"
2. **Sammeln** – Stammdaten aus `projekt.yaml`, Werte aus den Vertragsdateien
3. **Übersicht** – Tabelle mit Feld, Wert, Fundstelle, Status. Erst schauen, dann schreiben.
4. **Abfrage** – gebündelt nur die offenen Felder, nicht einzeln durchklicken
5. **Generieren** – DOCX nach `ausgang/<projekt>/`, benannt nach VA 1.3, dazu der Mail-Entwurf

Bei rechtlich scharfen Feldern (Fristen, Vertragsdatum, Paragrafen, Beträge)
wird nie stillschweigend geraten. Entweder steht die Fundstelle dabei –
Datei und Seite – oder das Feld wird gefragt.

## Neue Vorlage anlegen

Siehe [`vorlagen/README.md`](vorlagen/README.md). Kurzfassung: Ordner anlegen,
bestehendes Schreiben als `vorlage.docx` hineinlegen, die variablen Stellen
durch `{{platzhalter}}` ersetzen, `felder.yaml` dazu.

## Neues Projekt anlegen

Siehe [`projekte/README.md`](projekte/README.md). Kurzfassung: Es reicht die
Auftragsbestätigung – daraus lässt sich die `projekt.yaml` erzeugen.
Projekte werden angelegt, wenn Schriftverkehr ansteht, nicht auf Vorrat.

## Hotels für Monteure

Zweiter Teil im selben Repo: Unterkunft für eine Montage finden, ohne bei
jeder Suche wieder Adressen einzutippen. Baustellen und Monteure stehen einmal
in den Stammdaten, danach reicht ein Aufruf.

```bash
python3 werkzeuge/hotelsuche.py auftrag BHV 12.10.2026 16.10.2026 --monteure MK TS
```

Gesucht wird im Radius um die Baustellenkoordinate, nicht nach Ortsnamen: Ein
Hotel „in Fulda" kann zwölf Kilometer und zwei Ortsdurchfahrten entfernt
liegen. Die Verfügbarkeit kommt live aus der Hotelsuche, gefiltert auf
Einzelzimmer mit Dusche und WC, Frühstück, Parkplatz und mindestens gute
Bewertung. Bewertet und sortiert wird hier im Repo, nachvollziehbar aus
Entfernung, Preis je Zimmer und Nacht, Bewertung und Parkplatz.

Häuser ohne eigenen Stellplatz fallen raus. Ob das jeweilige Fahrzeug dort
auch hineinpasst, wird beim Haus geklärt und nicht gerechnet.

Liegt die Baustelle in Reichweite des Betriebssitzes, hängt die Auswertung eine
Gegenrechnung an: Zimmer, Diesel und Verpflegungspauschale gegen tägliches
Heimfahren, dazu die Fahrzeit. Bei Marburg mit zwei Mann und vier Nächten sind
das gut sechshundert Euro Unterschied.

Ab fünf Nächten kommt zusätzlich die Direktanfrage ans Hotel dazu, weil
Monteurpauschalen regelmäßig unter dem Portalpreis liegen. Jede Buchung landet
in `buchungen.yaml` samt Fazit, und beim nächsten Einsatz am selben Ort steht
oben, was dort funktioniert hat.

### Cockpit

Wer lieber klickt als tippt, erzeugt sich die Oberfläche dazu:

```bash
python3 werkzeuge/cockpit.py
```

Das Ergebnis ist **eine** HTML-Datei im Datenordner unter `hotels/cockpit.html`,
die per Doppelklick aufgeht und auch aus SharePoint heraus läuft. Baustelle aus
dem Dropdown, Monteure per Häkchen, Zeitraum, fertig: Daraus entsteht der
Auftragstext für Claude, der passende Kommandozeilenaufruf und als Notnagel ein
Booking-Link. Dazu der Belegungsplan und die Buchungshistorie.

Die Stammdaten stehen in der Datei drin, sie werden nicht nachgeladen. Nach
jeder Änderung an Baustellen oder Monteuren also neu erzeugen. Was die Seite
nicht kann, ist die Verfügbarkeit abfragen: Dafür fehlt einem Browser der
Zugang zu den Hotelportalen. Sie stellt die Anfrage zusammen, die Suche selbst
läuft über Claude.

Details: [`stammdaten/README.md`](stammdaten/README.md).

## Prüfen

```bash
python3 werkzeuge/pruefe_vorlage.py vorlagen/<name>    # Vorlage gegen felder.yaml
python3 -m unittest discover tests                     # Platzhalterersetzung
```

Die Tests sichern das Stück ab, an dem ein Fehler still bleibt: über Runs
verteilte Platzhalter, optionale Blöcke, Werktagsfristen. Ein Schreiben mit
falschem Wert sieht fertig aus – deshalb hier ein Netz. Für die Hotelsuche
gilt dasselbe: Entfernung zum falschen Punkt, ein Parkhaus, das als Stellplatz
durchgeht, ein Nachtpreis, der Zimmer und Nächte verwechselt.

Abhängigkeiten (`python-docx`, `PyYAML`) installiert der SessionStart-Hook in
`.claude/hooks/` automatisch. Lokal: `pip install -r requirements.txt`.
