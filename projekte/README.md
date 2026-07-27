# Projekte anlegen

**Echte Projekte gehören nicht in dieses Verzeichnis.** Sie liegen im
Datenordner auf deinem Rechner, damit keine Vertragsdaten ins Git wandern:

```bash
python3 werkzeuge/einrichten.py ~/Desktop/Vorlagenmanager-Daten   # einmalig
python3 werkzeuge/neues_projekt.py 2451 "Klinikum Beispielstadt"
```

Das legt `~/Desktop/Vorlagenmanager-Daten/projekte/2451_klinikum-beispielstadt/`
an. Hier im Repo bleiben nur diese Anleitung, die Musterdatei und ein
Beispielprojekt mit erfundenen Daten.

Aufgerufen werden Projekte danach über ihren Namen, nicht über den Pfad:

```bash
python3 werkzeuge/fuelle.py vorlagen/bedenkenanmeldung 2451_klinikum-beispielstadt --offen
```

Ein Ordner je Projekt, benannt `<projektnummer>_<kurzname>`.

```
projekte/2451_klinikum-xy/
  projekt.yaml    ← Stammdaten
  vertrag/        ← Vertragsrelevante Dateien
```

## Die projekt.yaml ist der Vertragsauszug

Das ist der Kniff, der den Aufwand klein hält: **Die Vertragswerte, die in
Schreiben auftauchen, ändern sich pro Projekt nicht.** Vertragsdatum,
Bestellnummer, Auftragssumme, Zahlungsziel, Ausführungsfristen – einmal
in die `projekt.yaml`, und ab da braucht kein einziges Schreiben mehr Zugriff
auf den Vertrag selbst.

Der Weg dahin: **eine Datei pro Projekt**, die Auftragsbestätigung. Darin steht
fast alles. Du lädst sie einmal hoch, daraus entsteht die `projekt.yaml`,
du liest sie gegen – fertig. Danach ist das Projekt dauerhaft versorgt, weil
die YAML im Repo liegt.

Lege Projekte an, wenn Schriftverkehr ansteht – nicht alle auf Vorrat.
Bei 30 Projekten sind selten mehr als eine Handvoll gleichzeitig aktiv.

## Was in `vertrag/` gehört

Der Ordner ist optional. Er ist für den Fall gedacht, dass ein Schreiben einen
Wert braucht, der **nicht** stabil ist und deshalb nicht in die `projekt.yaml`
gehört – etwa der Wortlaut einer bestimmten LV-Position oder der Bezug auf
einen konkreten Nachtrag. Dann legst du für diesen einen Vorgang die betroffene
Datei dazu.

Nicht: Fotos, Pläne, Mailverkehr, Protokolle. Die liefern keine Platzhalterwerte.

## projekt.yaml

Vorlage: [`_vorlage_projekt.yaml`](_vorlage_projekt.yaml)
Beispiel: [`2451_beispiel-klinikum/projekt.yaml`](2451_beispiel-klinikum/projekt.yaml)

Felder, die du nicht brauchst, kannst du weglassen. Felder, die in einer Vorlage
über `quelle: projekt` gezogen werden, müssen da sein – sonst wird gefragt.
