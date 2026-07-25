# Projekte anlegen

Ein Ordner je Projekt, benannt `<projektnummer>_<kurzname>`.

```
projekte/2451_klinikum-xy/
  projekt.yaml    ← Stammdaten
  vertrag/        ← Vertragsrelevante Dateien
```

## Der schnelle Weg

Du musst nicht den ganzen Projektordner bereitstellen. Für den Anfang reicht
**die Auftragsbestätigung** – darin stehen Auftraggeber, Anschrift, Vertrags­nummer,
Auftragsdatum und Bauvorhaben. Aus dieser einen Datei lässt sich die
`projekt.yaml` erzeugen, du liest sie einmal gegen und korrigierst.

Lege Projekte an, wenn Schriftverkehr ansteht – nicht alle auf Vorrat.

## Was in `vertrag/` gehört

Nur die Dateien, aus denen tatsächlich Werte für Schreiben gezogen werden:

- Auftragsbestätigung / Vertragsurkunde
- Leistungsverzeichnis (mindestens die betroffenen Positionen)
- Bauzeitenplan
- besondere Vertragsbedingungen, wenn sie von der VOB/B abweichen
- Nachträge, sobald es welche gibt

Nicht: Fotos, Pläne, Mailverkehr, Protokolle. Die liefern keine Platzhalterwerte
und machen die Suche nur langsamer.

## projekt.yaml

Vorlage: [`_vorlage_projekt.yaml`](_vorlage_projekt.yaml)
Beispiel: [`2451_beispiel-klinikum/projekt.yaml`](2451_beispiel-klinikum/projekt.yaml)

Felder, die du nicht brauchst, kannst du weglassen. Felder, die in einer Vorlage
über `quelle: projekt` gezogen werden, müssen da sein – sonst wird gefragt.
