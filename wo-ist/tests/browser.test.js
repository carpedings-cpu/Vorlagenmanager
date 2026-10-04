/* Wo ist's? · Autorin: Diana Ziegler */
const test = require('node:test');
const assert = require('node:assert/strict');
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
process.env.PW_EXPERIMENTAL_SERVICE_WORKER_NETWORK_EVENTS = '1';
const { chromium, devices } = require('playwright');

const WURZEL = path.join(__dirname, '..');
const FUSE_URL = 'https://cdn.jsdelivr.net/npm/fuse.js@7.1.0/dist/fuse.min.js';
const FUSE_DATEI = path.join(WURZEL, 'node_modules', 'fuse.js', 'dist', 'fuse.min.js');
const TYPEN = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.png': 'image/png' };

const UA_ANDROID = 'Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Mobile Safari/537.36';
const UA_IPHONE = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1';

let server, basis, browser;

test.before(async () => {
  server = http.createServer((req, res) => {
    const datei = path.join(WURZEL, decodeURIComponent(new URL(req.url, 'http://x').pathname));
    const ziel = fs.existsSync(datei) && fs.statSync(datei).isDirectory() ? path.join(datei, 'index.html') : datei;
    if (!ziel.startsWith(WURZEL) || !fs.existsSync(ziel)) { res.writeHead(404); return res.end(); }
    res.writeHead(200, { 'Content-Type': TYPEN[path.extname(ziel)] || 'application/octet-stream' });
    fs.createReadStream(ziel).pipe(res);
  });
  await new Promise(ok => server.listen(0, '127.0.0.1', ok));
  basis = `http://127.0.0.1:${server.address().port}/`;
  browser = await chromium.launch();
});

test.after(async () => {
  await browser.close();
  server.close();
});

const ATTRAPPE = () => {
  window.__gesagt = [];
  window.__saetze = [];
  window.__fehler = null;
  const echt = window.speechSynthesis;
  echt.speak = u => { if (u.text.trim()) window.__gesagt.push({ text: u.text, rate: Math.round(u.rate * 100) / 100, lang: u.lang }); };
  class Attrappe {
    start() {
      setTimeout(() => {
        if (window.__fehler) { this.onerror && this.onerror({ error: window.__fehler }); return this.onend(); }
        const satz = window.__saetze.shift() || '';
        if (satz) this.onresult({ results: [[{ transcript: satz }]] });
        this.onend();
      }, 30);
    }
    stop() {}
    abort() {}
  }
  window.SpeechRecognition = Attrappe;
  window.webkitSpeechRecognition = Attrappe;
};

async function neueSeite(optionen, vorbereitung) {
  const kontext = await browser.newContext(optionen);
  await kontext.route(FUSE_URL, r => r.fulfill({
    path: FUSE_DATEI, contentType: 'text/javascript', headers: { 'Access-Control-Allow-Origin': '*' }
  }));
  if (vorbereitung) await kontext.addInitScript(vorbereitung);
  const seite = await kontext.newPage();
  await seite.goto(basis);
  await seite.waitForFunction(() => typeof Fuse !== 'undefined');
  return { kontext, seite };
}

const android = { userAgent: UA_ANDROID, viewport: { width: 360, height: 740 }, hasTouch: true, isMobile: true, locale: 'de-DE' };
const iphone = { ...devices['iPhone 13'], userAgent: UA_IPHONE, locale: 'de-DE' };

async function sprich(seite, knopf, satz) {
  await seite.evaluate(s => window.__saetze.push(s), satz);
  await seite.click(knopf);
}
const sichtbar = seite => seite.locator('.screen:not([hidden])');
const zuletztGesagt = seite => seite.evaluate(() => window.__gesagt.at(-1));

test('Chrome Android: echte Spracherkennungs-Schnittstelle wird erkannt', async () => {
  const { kontext, seite } = await neueSeite(android);
  assert.equal(await seite.evaluate(() => typeof (window.SpeechRecognition || window.webkitSpeechRecognition)), 'function');
  assert.equal(await seite.getAttribute('html', 'data-hoeren'), 'ja');
  await kontext.close();
});

test('Safari iOS im Browser: Spracherkennung aktiv', async () => {
  const { kontext, seite } = await neueSeite(iphone, () => {
    window.webkitSpeechRecognition = class { start() {} abort() {} stop() {} };
  });
  assert.equal(await seite.getAttribute('html', 'data-hoeren'), 'ja');
  await kontext.close();
});

test('Safari iOS vom Home-Bildschirm: Fallback mit Textfeld', async () => {
  const { kontext, seite } = await neueSeite(iphone, () => {
    Object.defineProperty(navigator, 'standalone', { get: () => true });
    window.webkitSpeechRecognition = class { start() {} abort() {} stop() {} };
    window.speechSynthesis.speak = () => {};
  });
  assert.equal(await seite.getAttribute('html', 'data-hoeren'), 'nein');
  await seite.click('#b-ablegen');
  await assert.doesNotReject(seite.locator('#s-tippen').waitFor());
  assert.match(await seite.textContent('#s-tippen .hinweis'), /Tippen Sie auf das Mikrofon Ihrer Tastatur und sprechen Sie/);
  assert.equal(await seite.evaluate(() => document.activeElement.id), 'eingabe');
  await seite.fill('#eingabe', 'Brille liegt auf dem Nachttisch');
  await seite.click('#b-fertig');
  await seite.locator('#s-ok').waitFor();
  assert.equal(await seite.textContent('#ok-text'), 'Gespeichert: Brille, auf dem Nachttisch');
  await kontext.close();
});

test('Browser ohne Spracherkennung: Fallback mit Textfeld', async () => {
  const { kontext, seite } = await neueSeite(android, () => {
    delete window.SpeechRecognition;
    delete window.webkitSpeechRecognition;
  });
  assert.equal(await seite.getAttribute('html', 'data-hoeren'), 'nein');
  await seite.click('#b-suchen');
  await seite.locator('#s-tippen').waitFor();
  await kontext.close();
});

test('Mikrofon verweigert: Wechsel aufs Textfeld mit Begründung', async () => {
  const { kontext, seite } = await neueSeite(android, ATTRAPPE);
  await seite.evaluate(() => { window.__fehler = 'not-allowed'; });
  await seite.click('#b-ablegen');
  await seite.locator('#s-tippen').waitFor();
  assert.match(await seite.textContent('#tippen-grund'), /Mikrofon ist für diese App nicht freigegeben/);
  await kontext.close();
});

test('Ablegen, Suchen, Verlauf, Foto, Liste, Sicherung', async () => {
  const { kontext, seite } = await neueSeite(android, ATTRAPPE);

  const start = await seite.locator('#s-start').boundingBox();
  const k1 = await seite.locator('#b-ablegen').boundingBox();
  const k2 = await seite.locator('#b-suchen').boundingBox();
  assert.ok(k1.height >= 0.4 * 740 && k2.height >= 0.4 * 740, `Knopfhöhen ${k1.height} / ${k2.height}`);
  assert.ok(start.height <= 740, 'Startseite passt ohne Scrollen');
  assert.equal(await seite.evaluate(() => getComputedStyle(document.querySelector('#b-ablegen')).backgroundColor), 'rgb(27, 94, 32)');
  assert.equal(await seite.evaluate(() => getComputedStyle(document.querySelector('#b-suchen')).backgroundColor), 'rgb(13, 71, 161)');

  await sprich(seite, '#b-ablegen', 'Den Ersatzschlüssel fürs Auto hab ich in die blaue Dose im Flurschrank getan');
  await seite.locator('#s-ok').waitFor();
  assert.equal(await seite.textContent('#ok-text'), 'Gespeichert: Ersatzschlüssel fürs Auto, in der blauen Dose im Flurschrank');
  assert.deepEqual(await zuletztGesagt(seite), { text: 'Gespeichert: Ersatzschlüssel fürs Auto, in der blauen Dose im Flurschrank', rate: 0.9, lang: 'de-DE' });

  const bild = await seite.evaluate(() => {
    const c = document.createElement('canvas');
    c.width = 3000; c.height = 2000;
    const g = c.getContext('2d');
    g.fillStyle = '#4a7'; g.fillRect(0, 0, 3000, 2000);
    return c.toDataURL('image/png').split(',')[1];
  });
  await seite.setInputFiles('#foto-input', { name: 'ort.png', mimeType: 'image/png', buffer: Buffer.from(bild, 'base64') });
  await seite.locator('#ok-foto:not([hidden])').waitFor();
  const foto = await seite.evaluate(async () => {
    const d = await new Promise(ok => { const r = indexedDB.open('wo-ists'); r.onsuccess = () => ok(r.result); });
    const alle = await new Promise(ok => { const r = d.transaction('eintraege').objectStore('eintraege').getAll(); r.onsuccess = () => ok(r.result); });
    const f = alle[0].foto;
    const img = await createImageBitmap(new Blob([f.daten], { type: f.typ }));
    return { typ: f.typ, breite: img.width, hoehe: img.height, arrayBuffer: f.daten instanceof ArrayBuffer };
  });
  assert.deepEqual(foto, { typ: 'image/jpeg', breite: 1200, hoehe: 800, arrayBuffer: true });
  assert.equal((await zuletztGesagt(seite)).text, 'Foto gespeichert.');

  await seite.click('#b-stimmt');
  await seite.locator('#s-start').waitFor();

  await sprich(seite, '#b-suchen', 'Wo ist der Autoschlüssel?');
  await seite.locator('#s-treffer').waitFor();
  assert.equal(await seite.textContent('#treffer .ding'), 'Ersatzschlüssel fürs Auto');
  assert.equal(await seite.textContent('#treffer .ort'), 'In der blauen Dose im Flurschrank');
  assert.equal(await seite.locator('#treffer img.foto').count(), 1);
  assert.equal((await zuletztGesagt(seite)).text, 'Der Ersatzschlüssel fürs Auto ist in der blauen Dose im Flurschrank.');
  await seite.click('#s-treffer [data-aktion="start"]');

  for (let runde = 0; runde < 2; runde++) {
    await seite.waitForTimeout(200);
    await sprich(seite, runde ? '#s-treffer [data-aktion="suchen"]' : '#b-suchen', 'Wo ist der Autoschlüssel?');
    await seite.waitForTimeout(200);
    await seite.locator('#s-treffer').waitFor();
    assert.equal(await seite.evaluate(() => document.querySelector('#treffer img.foto').naturalWidth), 1200, `Foto bei Frage ${runde + 2}`);
  }
  await seite.click('#s-treffer [data-aktion="start"]');

  await sprich(seite, '#b-ablegen', 'Den Ersatzschlüssel fürs Auto hab ich ans Schlüsselbrett gehängt');
  await seite.locator('#s-frage').waitFor();
  assert.equal(await seite.textContent('#frage-text'), 'Meinen Sie den Ersatzschlüssel fürs Auto von vorher?');
  await seite.click('#b-ja');
  await seite.locator('#s-ok').waitFor();
  assert.equal(await seite.textContent('#ok-text'), 'Gespeichert: Ersatzschlüssel fürs Auto, am Schlüsselbrett');
  await seite.click('#b-stimmt');

  await sprich(seite, '#b-suchen', 'Wo ist der Ersatzschlüssel?');
  await seite.locator('#s-treffer').waitFor();
  assert.equal(await seite.textContent('#treffer .ort'), 'Am Schlüsselbrett');
  assert.match(await seite.locator('#treffer .klein').last().textContent(), /^Vorher lag er: in der blauen Dose im Flurschrank \(/);
  assert.equal(await seite.locator('#treffer img.foto').count(), 0, 'altes Foto zeigt den alten Ort und fällt weg');
  await seite.click('#s-treffer [data-aktion="start"]');

  await sprich(seite, '#b-ablegen', 'Die Lesebrille ist im Auto');
  await seite.locator('#s-ok').waitFor();
  await sprich(seite, '#b-nochmal', 'Die Lesebrille ist auf dem Klavier');
  await seite.waitForFunction(() => /Klavier/.test(document.querySelector('#ok-text').textContent));
  assert.equal(await seite.textContent('#ok-text'), 'Gespeichert: Lesebrille, auf dem Klavier');
  await seite.click('#b-stimmt');
  await sprich(seite, '#b-ablegen', 'Die Sonnenbrille ist im Handschuhfach');
  await seite.waitForFunction(() => /Sonnenbrille/.test(document.querySelector('#ok-text').textContent));
  await seite.setInputFiles('#foto-input', { name: 'ort.png', mimeType: 'image/png', buffer: Buffer.from(bild, 'base64') });
  await seite.locator('#ok-foto:not([hidden])').waitFor();
  await seite.click('#b-stimmt');

  await sprich(seite, '#b-suchen', 'Wo ist die Brille?');
  await seite.locator('#s-treffer').waitFor();
  assert.equal(await seite.locator('#treffer .karte.wahl').count(), 2);
  await seite.locator('#treffer .karte.wahl', { hasText: 'Lesebrille' }).click();
  assert.equal(await seite.textContent('#treffer .ort'), 'Auf dem Klavier');
  await seite.click('#s-treffer [data-aktion="start"]');

  await sprich(seite, '#b-suchen', 'Wo ist mein Regenschirm?');
  await seite.locator('#s-treffer').waitFor();
  assert.equal(await seite.textContent('#treffer'), 'Dazu habe ich nichts gespeichert.');
  assert.equal((await zuletztGesagt(seite)).text, 'Dazu habe ich nichts gespeichert.');
  await seite.click('#s-treffer [data-aktion="start"]');

  await seite.click('#b-suchen');
  await seite.locator('#s-nichts').waitFor();
  assert.match((await zuletztGesagt(seite)).text, /nichts gehört/);
  await seite.click('#s-nichts [data-aktion="start"]');

  await seite.click('#b-liste');
  await seite.locator('#s-liste').waitFor();
  assert.equal(await seite.locator('#liste li').count(), 3);
  assert.equal(await seite.textContent('#liste-anzahl'), '3 Einträge gespeichert.');

  const [download] = await Promise.all([seite.waitForEvent('download'), seite.click('#b-export')]);
  const sicherung = JSON.parse(fs.readFileSync(await download.path(), 'utf8'));
  assert.equal(sicherung.eintraege.length, 3);
  assert.equal(sicherung.autorin, 'Diana Ziegler');

  await seite.locator('#liste li', { hasText: 'Sonnenbrille' }).getByRole('button', { name: 'Löschen' }).click();
  await seite.locator('#s-loeschen').waitFor();
  assert.equal(await seite.textContent('#loeschen-text'), 'Wirklich löschen: Sonnenbrille?');
  await seite.click('#s-loeschen [data-aktion="liste"]');
  await seite.locator('#s-liste').waitFor();
  assert.equal(await seite.locator('#liste li').count(), 3, 'Nein, behalten löscht nichts');
  await seite.locator('#liste li', { hasText: 'Sonnenbrille' }).getByRole('button', { name: 'Löschen' }).click();
  await seite.click('#b-loeschen-ja');
  await seite.locator('#s-liste').waitFor();
  assert.equal(await seite.locator('#liste li').count(), 2);
  assert.equal(await seite.textContent('#liste-meldung'), 'Gelöscht.');

  await seite.setInputFiles('#import-input', { name: 'sicherung.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(sicherung)) });
  await seite.waitForFunction(() => document.querySelector('#liste-meldung').textContent === '3 Einträge geladen.');
  assert.equal(await seite.locator('#liste li').count(), 3);
  const mitFoto = await seite.locator('#liste li', { hasText: 'mit Foto' }).count();
  assert.equal(mitFoto, 1, 'Foto übersteht Sicherung und Laden');

  await seite.setInputFiles('#import-input', { name: 'kaputt.json', mimeType: 'application/json', buffer: Buffer.from('kein json') });
  await seite.waitForFunction(() => document.querySelector('#liste-meldung').textContent === 'Diese Datei kann ich nicht lesen.');

  await seite.goBack();
  await seite.locator('#s-start').waitFor();

  await kontext.close();
});

test('Nochmal vorlesen und Liegt jetzt woanders', async () => {
  const { kontext, seite } = await neueSeite(android, ATTRAPPE);
  await sprich(seite, '#b-ablegen', 'Den Ersatzschlüssel fürs Auto hab ich in die blaue Dose im Flurschrank getan');
  await seite.locator('#s-ok').waitFor();
  await seite.click('#b-stimmt');
  await seite.waitForTimeout(200);

  await sprich(seite, '#b-suchen', 'Wo ist der Autoschlüssel?');
  await seite.locator('#s-treffer').waitFor();
  await seite.evaluate(() => { window.__gesagt = []; });
  await seite.getByRole('button', { name: 'Nochmal vorlesen' }).click();
  assert.equal((await zuletztGesagt(seite)).text, 'Der Ersatzschlüssel fürs Auto ist in der blauen Dose im Flurschrank.');

  await sprich(seite, 'text=Liegt jetzt woanders', 'In den Küchenschrank');
  await seite.waitForFunction(() => /Küchenschrank/.test(document.querySelector('#ok-text').textContent));
  assert.equal(await seite.textContent('#hoeren-titel'), 'Wo liegt der Ersatzschlüssel fürs Auto jetzt?');
  assert.equal(await seite.textContent('#ok-text'), 'Gespeichert: Ersatzschlüssel fürs Auto, im Küchenschrank');
  await seite.click('#b-stimmt');
  await seite.waitForTimeout(200);

  await sprich(seite, '#b-suchen', 'Wo ist der Ersatzschlüssel?');
  await seite.locator('#s-treffer').waitFor();
  assert.equal(await seite.textContent('#treffer .ort'), 'Im Küchenschrank');
  assert.match(await seite.locator('#treffer .karte .klein').last().textContent(), /^Vorher lag er: in der blauen Dose im Flurschrank/);
  assert.equal((await zuletztGesagt(seite)).text, 'Der Ersatzschlüssel fürs Auto ist im Küchenschrank.');
  assert.equal(await seite.evaluate(async () => {
    const d = await new Promise(ok => { const r = indexedDB.open('wo-ists'); r.onsuccess = () => ok(r.result); });
    return new Promise(ok => { const r = d.transaction('eintraege').objectStore('eintraege').count(); r.onsuccess = () => ok(r.result); });
  }), 1, 'kein zweiter Eintrag');
  await kontext.close();
});

test('Erinnerung an die Sicherung', async () => {
  const { kontext, seite } = await neueSeite(android, ATTRAPPE);
  assert.equal(await seite.isVisible('#erinnerung'), false);
  await seite.evaluate(() => {
    localStorage.setItem('woists.seit', '3');
    localStorage.setItem('woists.bezug', new Date(Date.now() - 31 * 864e5).toISOString());
  });
  await seite.reload();
  await seite.locator('#erinnerung').waitFor();
  await seite.click('#b-erinnerung-spaeter');
  assert.equal(await seite.isVisible('#erinnerung'), false);
  assert.match((await zuletztGesagt(seite)).text, /in einer Woche/);

  await seite.evaluate(() => { localStorage.setItem('woists.seit', '20'); localStorage.removeItem('woists.spaeter'); });
  await seite.click('#b-liste');
  await seite.click('#s-liste [data-aktion="start"] >> nth=0');
  await seite.locator('#erinnerung').waitFor();
  const [download] = await Promise.all([seite.waitForEvent('download'), seite.click('#b-erinnerung-ja')]);
  assert.ok(download);
  await seite.waitForFunction(() => document.querySelector('#erinnerung').hidden);
  assert.equal(await seite.evaluate(() => localStorage.getItem('woists.seit')), '0');
  await kontext.close();
});

test('Gestaltung: Schriftgröße, Breite 360 px, keine Icons ohne Text', async () => {
  const { kontext, seite } = await neueSeite(android, ATTRAPPE);
  await sprich(seite, '#b-ablegen', 'Brille liegt auf dem Nachttisch');
  await seite.locator('#s-ok').waitFor();
  for (const name of ['start', 'hoeren', 'tippen', 'nichts', 'frage', 'ok', 'treffer', 'liste', 'loeschen']) {
    const pruefung = await seite.evaluate(n => {
      document.querySelectorAll('.screen').forEach(s => { s.hidden = s.id !== 's-' + n; });
      const zuKlein = [];
      for (const e of document.querySelectorAll(`#s-${n} *`)) {
        if (e.closest('.unsichtbar') || !e.offsetParent) continue;
        const eigenerText = [...e.childNodes].some(k => k.nodeType === 3 && k.textContent.trim());
        if (eigenerText && parseFloat(getComputedStyle(e).fontSize) < 22) zuKlein.push(e.outerHTML.slice(0, 60));
      }
      const leereKnoepfe = [...document.querySelectorAll(`#s-${n} button`)].filter(b => b.offsetParent && !b.textContent.trim());
      return { zuKlein, leer: leereKnoepfe.length, breite: document.documentElement.scrollWidth };
    }, name);
    assert.deepEqual(pruefung.zuKlein, [], `Bildschirm ${name}`);
    assert.equal(pruefung.leer, 0, `Bildschirm ${name}: Knopf ohne Text`);
    assert.ok(pruefung.breite <= 360, `Bildschirm ${name}: ${pruefung.breite}px breit`);
  }
  assert.ok(parseFloat(await seite.evaluate(() => getComputedStyle(document.querySelector('.ergebnis')).fontSize)) >= 32);
  await kontext.close();
});

test('Offline: App und Fuse.js kommen aus dem Service Worker', async () => {
  const { kontext, seite } = await neueSeite(android, ATTRAPPE);
  await seite.evaluate(() => navigator.serviceWorker.ready);
  await seite.waitForFunction(async () => {
    const c = await caches.open('wo-ists-v3');
    return (await c.keys()).length >= 10;
  });
  await kontext.setOffline(true);
  await seite.reload();
  await seite.waitForFunction(() => typeof Fuse !== 'undefined');
  assert.equal(await seite.textContent('#b-ablegen'), 'Ich lege etwas ab');
  await kontext.close();
});
