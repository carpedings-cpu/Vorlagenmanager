# Wo ist's?

Autorin: Diana Ziegler

Man sagt dem Handy, wo man etwas hingelegt hat, und fragt später einfach „Wo ist der Autoschlüssel?“. Die App liest die Antwort groß vor. Gedacht für Menschen, die mit Technik wenig zu tun haben wollen: zwei Knöpfe, große Schrift, keine Anmeldung.

Alle Einträge bleiben auf dem Gerät (IndexedDB). Es gibt keinen Server, kein Konto und keine Statistik. Die App funktioniert nach dem ersten Öffnen auch ohne Internet.

## Auf dem Startbildschirm ablegen

Damit die App wie eine normale App mit eigenem Symbol startet, einmal auf den Startbildschirm legen. Das ist auch für die Datensicherheit wichtig: Auf dem iPhone löscht Safari Daten von Webseiten, die sieben Tage nicht geöffnet wurden. Für Apps auf dem Home-Bildschirm gilt das nicht.

### iPhone (Safari)

1. Die Adresse der App in **Safari** öffnen. Andere Browser auf dem iPhone können das nicht zuverlässig.
2. Unten auf das **Teilen-Symbol** tippen (Viereck mit Pfeil nach oben).
3. Etwas nach unten wischen und **„Zum Home-Bildschirm“** wählen.
4. Der Name „Wo ist's?“ ist schon eingetragen. Oben rechts auf **„Hinzufügen“** tippen.
5. Das blaue Symbol mit der Lupe liegt jetzt auf dem Home-Bildschirm.

Wichtig fürs iPhone: Vom Home-Bildschirm aus erlaubt Apple keine Spracherkennung innerhalb der App. Die App zeigt dann ein großes Textfeld. Dort auf das **Mikrofon unten auf der Tastatur** tippen und sprechen. Falls das Mikrofon auf der Tastatur fehlt: Einstellungen → Allgemein → Tastatur → **Diktierfunktion** einschalten.

### Android (Chrome)

1. Die Adresse der App in **Chrome** öffnen.
2. Oben rechts auf die **drei Punkte** tippen.
3. **„App installieren“** oder **„Zum Startbildschirm hinzufügen“** wählen.
4. Mit **„Installieren“** bzw. **„Hinzufügen“** bestätigen.
5. Beim ersten Tippen auf „Ich lege etwas ab“ fragt Chrome nach dem Mikrofon. Hier **„Zulassen“** wählen.

## So wird sie benutzt

**Ich lege etwas ab** (grün): Antippen und frei sprechen, zum Beispiel „Den Ersatzschlüssel fürs Auto hab ich in die blaue Dose im Flurschrank getan“. Die Aufnahme endet von selbst, sobald man aufhört zu sprechen. Die App zeigt und sagt „Gespeichert: Ersatzschlüssel fürs Auto, in der blauen Dose im Flurschrank“. Mit **Stimmt** ist alles erledigt, mit **Nochmal** wird der Eintrag verworfen und neu aufgenommen, mit **Foto vom Ort** kommt ein Bild dazu.

Gibt es den Gegenstand schon, fragt die App nach („Meinen Sie den Ersatzschlüssel fürs Auto von vorher?“). Bei **Ja** wird der alte Ort im Verlauf gemerkt.

**Wo ist …?** (blau): Antippen und fragen, zum Beispiel „Wo ist der Autoschlüssel?“. Die App zeigt den Ort groß, mit Foto, und liest ihn vor. Darunter steht klein, wo der Gegenstand vorher lag. Passen mehrere Einträge, erscheinen bis zu drei große Karten zur Auswahl. Mit **Nochmal vorlesen** wiederholt die App die Antwort. Mit **Liegt jetzt woanders** sagt man nur den neuen Ort („Im Küchenschrank“), der alte wandert in den Verlauf.

Die Suche kennt gängige andere Wörter für dasselbe Ding: Wer nach dem Portemonnaie fragt, findet auch die Geldbörse, Medikamente finden Tabletten, Telefon findet Handy.

**Alle Einträge** (Link unten): Liste mit Löschen-Knopf und Rückfrage. Dort auch **Sicherung speichern** und **Sicherung laden** (JSON-Datei mit allen Einträgen und Fotos). Eine Sicherung ab und zu, etwa per E-Mail an sich selbst, schützt vor Datenverlust bei Handywechsel oder -defekt. Nach 20 neuen Einträgen oder 30 Tagen ohne Sicherung fragt die App auf dem Startbildschirm einmal nach. „Später“ verschiebt die Frage um eine Woche.

## Datenschutz

Die App selbst speichert und sendet nichts nach außen. Die Spracherkennung übernimmt aber der Browser: Chrome schickt die Aufnahme dafür an Google, Safari an Apple (Siri). Wer das nicht möchte, tippt auf „Lieber tippen“ und nutzt die Tastatur. Fuse.js (Suche) wird einmalig von cdn.jsdelivr.net geladen und dann aus dem Gerätespeicher genutzt.

## Technik

Vanilla HTML, CSS und JavaScript ohne Build-Schritt. Alle Pfade sind relativ, der Ordner lässt sich so wie er ist auf GitHub Pages oder jeden anderen Webspace legen. Spracherkennung und Service Worker brauchen HTTPS (oder `localhost` zum Testen).

| Datei | Inhalt |
| --- | --- |
| `index.html` | Alle Bildschirme |
| `app.js` | Satz zerlegen, Suche, IndexedDB, Sprache, Bedienung |
| `style.css` | Gestaltung (Kontrast WCAG AAA, Grundschrift 24 px, Ergebnisse 32 px) |
| `service-worker.js` | Offline-Cache inkl. Fuse.js |
| `manifest.json` | PWA-Angaben |
| `icons/` | App-Symbole |
| `tests/` | Tests |

Datenmodell eines Eintrags:

```js
{ id, gegenstand, ort, originalsatz, foto /* optional */, erstellt, verlauf: [{ ort, datum }] }
```

`foto` liegt als `{ typ, daten }` mit einem ArrayBuffer in IndexedDB und wird erst beim Anzeigen wieder zum Blob. Safari auf dem iPhone verliert Blobs aus IndexedDB sonst gelegentlich, das Foto fehlt dann beim zweiten Aufruf. Einträge im alten Format (direkter Blob) liest die App weiterhin.

`erstellt` ist der Zeitpunkt, an dem der aktuelle Ort gespeichert wurde. Beim Umlegen wandert der alte Ort mit seinem Datum in `verlauf` (neuester zuerst, höchstens zehn). Ein altes Foto wird dabei verworfen, weil es den alten Ort zeigt.

Lässt sich ein Satz nicht sicher in Gegenstand und Ort zerlegen (z. B. „Zweitschlüssel hat die Nachbarin“), steht der ganze Satz in `gegenstand` und `originalsatz`, `ort` bleibt leer. Die Suche findet ihn trotzdem.

### Auf GitHub Pages veröffentlichen

Am saubersten in einem eigenen, öffentlichen Repository, in dem der Inhalt dieses Ordners im Hauptverzeichnis liegt. Dann unter Settings → Pages die Quelle „Deploy from a branch“, Branch `main`, Ordner `/ (root)` wählen. Die App ist danach unter `https://<benutzer>.github.io/<repo>/` erreichbar.

Neue Version ausliefern: In `service-worker.js` die Konstante `CACHE` hochzählen (`wo-ists-v2` …). Geänderte Dateien kommen sonst erst beim übernächsten Start an.

### Tests

```bash
npm install
npm test              # Satz zerlegen, Suche, Kontrast
npm run test:browser  # Bedienung in Chromium, Android- und iPhone-Emulation
```

`npm test` prüft das Zerlegen an 29 deutschen Beispielsätzen und 8 reinen Ortsangaben (darunter „hab den Pass in die Schublade getan“, „Brille liegt auf dem Nachttisch“, „Äh, also die Brille ist auf dem Klavier.“), die Suche mit und ohne Fuse.js samt Synonymen, die Rückfragen und alle Farbpaare auf mindestens 7:1.

`npm run test:browser` spielt die Bedienung in Chromium durch: Erkennung der Sprach-Schnittstelle (Android-Chrome, Safari im Browser, Safari vom Home-Bildschirm mit Fallback, Browser ohne Schnittstelle, verweigertes Mikrofon), Ablegen, Rückfrage bei gleichem Gegenstand, Verlauf, Foto auf 1200 px und JPEG, mehrere Treffer, kein Treffer, Löschen mit Rückfrage, Sicherung und Laden, Nochmal vorlesen, Liegt jetzt woanders, Erinnerung an die Sicherung, Schriftgrößen, 360 px Breite und Offline-Start. Die Spracherkennung selbst wird dabei durch eine Attrappe ersetzt.

### Noch auf echten Geräten zu prüfen

Ein Emulator ersetzt kein echtes Handy. Vor der Weitergabe einmal auf einem Android-Handy mit Chrome und einem iPhone mit Safari prüfen: Mikrofon-Abfrage, Ende der Aufnahme bei Sprechpause, deutsche Stimme beim Vorlesen, Kamera bei „Foto vom Ort“, Diktat über die Tastatur im Home-Bildschirm-Modus auf dem iPhone und Start im Flugmodus.
