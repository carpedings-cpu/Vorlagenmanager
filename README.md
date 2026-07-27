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
| `werkzeuge/` | Skripte zum Einrichten, Prüfen und Ausfüllen |
| `tests/` | Regressionstests der Platzhalterersetzung |
| `.claude/skills/schriftverkehr/` | Der Skill, der die Generierung steuert |

**Im Datenordner, z. B. `~/Desktop/Vorlagenmanager-Daten/`:**

| Ordner | Inhalt |
|---|---|
| `projekte/` | Je Projekt: `projekt.yaml` (Stammdaten) + `vertrag/` (bei Bedarf) |
| `ausgang/` | Die generierten Schreiben, nach Projekt sortiert |

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

## Prüfen

```bash
python3 werkzeuge/pruefe_vorlage.py vorlagen/<name>    # Vorlage gegen felder.yaml
python3 -m unittest discover tests                     # Platzhalterersetzung
```

Die Tests sichern das Stück ab, an dem ein Fehler still bleibt: über Runs
verteilte Platzhalter, optionale Blöcke, Werktagsfristen. Ein Schreiben mit
falschem Wert sieht fertig aus – deshalb hier ein Netz.

Abhängigkeiten (`python-docx`, `PyYAML`) installiert der SessionStart-Hook in
`.claude/hooks/` automatisch. Lokal: `pip install -r requirements.txt`.
