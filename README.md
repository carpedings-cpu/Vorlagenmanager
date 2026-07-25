# Vorlagenmanager – Generator für wiederkehrenden Schriftverkehr

Erzeugt aus einer Vorlage mit Platzhaltern und den Projektdaten ein
fertiges Schreiben (DOCX) plus passenden Mail-Entwurf.

Der Kern der Idee: **Jeder Platzhalter weiß, woher sein Wert kommt.**
Dadurch wird vor der Generierung nur das gefragt, was wirklich fallspezifisch
ist – alles andere kommt aus den Projektstammdaten oder den Vertragsdateien.

## Ordner

| Ordner | Inhalt |
|---|---|
| `vorlagen/` | Je Schreiben ein Ordner: die DOCX-Vorlage, `felder.yaml`, `mail.md` |
| `projekte/` | Je Projekt ein Ordner: `projekt.yaml` (Stammdaten) + `vertrag/` (Vertragsdateien) |
| `ausgang/` | Die generierten Schreiben, nach Projekt sortiert |
| `werkzeuge/` | Skripte zum Prüfen und Ausfüllen |
| `.claude/skills/schriftverkehr/` | Der Skill, der die Generierung steuert |

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
python3 werkzeuge/pruefe_vorlage.py vorlagen/<name>
```

Meldet Platzhalter ohne Felddefinition und Felder ohne Platzhalter.
