/* Wo ist's? · Autorin: Diana Ziegler */
const test = require('node:test');
const assert = require('node:assert/strict');
const app = require('../app.js');

const saetze = [
  'Den Ersatzschlüssel fürs Auto hab ich in die blaue Dose im Flurschrank getan',
  'Brille liegt auf dem Nachttisch',
  'Die Lesebrille ist im Auto',
  'Den Schlüssel für den Keller hab ich zwischen die Bücher im Regal gelegt',
  'Pass ins Handschuhfach',
  'Mein Impfpass ist in der Handtasche',
  'Die Fernbedienung hab ich aufs Regal gelegt',
  'Zweitschlüssel hat die Nachbarin',
  'Hab das Ladekabel vom Handy in die Küchenschublade gesteckt',
  'Weihnachtsdeko auf den Dachboden gebracht'
];
const liste = saetze.map((s, i) => {
  const p = app.zerlege(s);
  return { id: String(i), gegenstand: p.gegenstand, ort: p.ort, originalsatz: s, erstellt: '2026-10-01T10:00:00Z', verlauf: [] };
});
const namen = (frage) => app.suche(frage, liste).map(e => e.gegenstand);

for (const [mitFuse, titel] of [[true, 'mit Fuse.js'], [false, 'ohne Fuse.js (Notlösung)']]) {
  test.describe(titel, () => {
    test.before(() => { global.Fuse = mitFuse ? require('fuse.js') : undefined; });

    test('Fragewörter und Artikel fallen weg', () => {
      assert.equal(app.frageBereinigen('Wo ist der Autoschlüssel?'), 'autoschlüssel');
      assert.equal(app.frageBereinigen('Wo hab ich nur meine Brille hingelegt?'), 'brille');
      assert.equal(app.frageBereinigen('Wo sind denn die Weihnachtssachen'), 'weihnachtssachen');
    });

    test('ein klarer Treffer', () => {
      assert.deepEqual(namen('Wo ist der Autoschlüssel?'), ['Ersatzschlüssel fürs Auto']);
      assert.deepEqual(namen('Wo ist der Kellerschlüssel?'), ['Schlüssel für den Keller']);
      assert.deepEqual(namen('Wo ist meine Brille?'), ['Brille']);
      assert.deepEqual(namen('Wo ist die Fernbedienung?'), ['Fernbedienung']);
      assert.deepEqual(namen('Wo ist das Handyladekabel?'), ['Ladekabel vom Handy']);
    });

    test('unsicher gespeicherte Sätze sind auffindbar', () => {
      assert.deepEqual(namen('Wo ist der Zweitschlüssel?'), ['Zweitschlüssel hat die Nachbarin']);
    });

    test('mehrere ähnliche Treffer, höchstens drei', () => {
      const r = namen('Wo ist der Schlüssel?');
      assert.ok(r.length >= 2 && r.length <= 3, r.join(' | '));
    });

    test('kein Treffer', () => {
      assert.deepEqual(namen('Wo ist mein Regenschirm?'), []);
      assert.deepEqual(namen('Wo ist?'), []);
    });
  });
}

test.describe('Doppelte Gegenstände', () => {
  test.before(() => { global.Fuse = require('fuse.js'); });
  test('erkennt denselben Gegenstand', () => {
    assert.equal(app.findeDoppelt('Ersatzschlüssel fürs Auto', liste).id, '0');
    assert.equal(app.findeDoppelt('Ersatzschlüssel', liste).id, '0');
    assert.equal(app.findeDoppelt('Fernbedienung', liste).id, '6');
  });
  test('fragt nicht bei nur entfernt Ähnlichem', () => {
    assert.equal(app.findeDoppelt('Handy', liste), null);
    assert.equal(app.findeDoppelt('Kamm', liste), null);
    assert.equal(app.findeDoppelt('Schlüssel', liste), null);
  });
  test('Rückfrage mit passendem Artikel', () => {
    assert.equal(app.rueckfrage(liste[0]), 'Meinen Sie den Ersatzschlüssel fürs Auto von vorher?');
    assert.equal(app.rueckfrage(liste[6]), 'Meinen Sie die Fernbedienung von vorher?');
    assert.equal(app.rueckfrage(liste[1]), 'Meinen Sie diesen Eintrag von vorher: Brille?');
  });
});

test('Antwortsätze', () => {
  assert.equal(app.antwortSatz(liste[0]), 'Der Ersatzschlüssel fürs Auto ist in der blauen Dose im Flurschrank.');
  assert.equal(app.antwortSatz(liste[1]), 'Brille: auf dem Nachttisch.');
  assert.equal(app.antwortSatz(liste[7]), 'Zweitschlüssel hat die Nachbarin.');
  assert.match(app.vorherSatz(liste[0], { ort: 'in der Küche', datum: '2026-10-02T08:00:00Z' }), /^Vorher lag er: in der Küche \(2\. Oktober 2026\)$/);
});
