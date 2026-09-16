# Loslegen mit der Hotelsuche

Zwei Wege. Der erste geht sofort und überall, auch vom iPad aus. Der zweite
ist der volle Funktionsumfang und braucht einmal zehn Minuten am Rechner.

## Weg 1: Cockpit plus Chat

Funktioniert ohne Installation, auf jedem Gerät.

1. Die Datei `cockpit.html` aus dem Chat in die Dateien-App speichern, am
   besten in einen Ordner, den du wiederfindest.
2. Antippen. Sie öffnet sich im Browser, alle Baustellen und Monteure sind drin.
3. Baustelle wählen, Leute anhaken, Zeitraum eintragen.
4. **Auftrag kopieren** drücken.
5. In einen Chat mit Claude einfügen und abschicken.

Der Auftragstext trägt alles, was für die Suche gebraucht wird: Koordinaten,
Radius, Preislimit, Fahrzeughöhe, Zimmerzahl und die beiden Regeln, an denen
sonst eine Buchung scheitert. Er funktioniert deshalb auch in einem frischen
Chat, der dieses Repo gar nicht kennt.

Was auf diesem Weg fehlt: Buchungen und Höhen, die du im Cockpit einträgst,
bleiben im Browser des Geräts. Sie wandern nicht von selbst in den Datenordner
zurück. Für ein paar Einträge reicht der Exportknopf, auf Dauer lohnt Weg 2.

## Weg 2: Alles lokal

Einmalig einrichten, danach läuft die Historie mit.

```bash
git clone https://github.com/carpedings-cpu/Vorlagenmanager.git
cd Vorlagenmanager
git checkout claude/hotel-booking-app-monteure-t84k31
pip install -r requirements.txt
python3 werkzeuge/einrichten.py ~/Desktop/Vorlagenmanager-Daten
```

Danach die drei Dateien aus dem Chat nach
`~/Desktop/Vorlagenmanager-Daten/hotels/` legen:

| Datei | Inhalt |
|---|---|
| `baustellen.yaml` | die 15 Baustellen |
| `monteure.yaml` | MS, HN, KH und du |
| `hoehen.yaml` | die fünf geprüften Durchfahrtshöhen |

Dann einmal:

```bash
python3 werkzeuge/cockpit.py
```

Das Cockpit liegt danach unter
`~/Desktop/Vorlagenmanager-Daten/hotels/cockpit.html`.

Ab jetzt reicht in Claude Code, geöffnet auf diesem Repo, ein Satz:

> Hotel für GAZ, 28.09. bis 02.10., MS HN KH

Der Skill macht den Rest: Stammdaten auflösen, suchen, Entfernungen rechnen,
Höhen erfragen, drei Vorschläge zeigen. Nach der Buchung festhalten:

```bash
python3 werkzeuge/hotelsuche.py buchen <auftrag.json> --hotel "<Name>" \
    --preis <EUR/Nacht> --fazit "Durchfahrt 3,20 m, Frühstück ab 6:00"
```

## Wenn sich etwas ändert

Neue Baustelle, neuer Monteur, neues Fahrzeug: erst die YAML im Datenordner
ändern, dann `python3 werkzeuge/cockpit.py`. Sonst zeigt das Cockpit weiter
den alten Stand, ohne das zu merken.

## Was die Suche nicht kann

Ohne Zugang zu den Hotelportalen keine Verfügbarkeit. Das Cockpit stellt die
Anfrage zusammen, die Suche selbst läuft über Claude. Der Booking-Link in der
Suchmaske ist der Notnagel: Er trägt Ort, Zeitraum und Zimmerzahl, die
Feinfilter setzt du dort selbst.
