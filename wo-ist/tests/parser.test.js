/* Wo ist's? · Autorin: Diana Ziegler */
const test = require('node:test');
const assert = require('node:assert/strict');
const { zerlege } = require('../app.js');

const faelle = [
  ['Den Ersatzschlüssel fürs Auto hab ich in die blaue Dose im Flurschrank getan', 'Ersatzschlüssel fürs Auto', 'in der blauen Dose im Flurschrank', 'm'],
  ['hab den Pass in die Schublade getan', 'Pass', 'in der Schublade', 'm'],
  ['Brille liegt auf dem Nachttisch', 'Brille', 'auf dem Nachttisch', null],
  ['Ich habe meine Brille auf den Nachttisch gelegt', 'Brille', 'auf dem Nachttisch', 'f'],
  ['Die Winterjacken sind oben im Kleiderschrank', 'Winterjacken', 'oben im Kleiderschrank', 'p'],
  ['Ich lege den Ersatzschlüssel unter die Fußmatte', 'Ersatzschlüssel', 'unter der Fußmatte', 'm'],
  ['Den Schlüssel für den Keller hab ich zwischen die Bücher im Regal gelegt', 'Schlüssel für den Keller', 'zwischen den Büchern im Regal', 'm'],
  ['Pass ins Handschuhfach', 'Pass', 'im Handschuhfach', null],
  ['Die Fernbedienung hab ich aufs Regal gelegt', 'Fernbedienung', 'auf dem Regal', 'f'],
  ['In der Schublade liegt die Schere', 'Schere', 'in der Schublade', 'f'],
  ['Mein Impfpass ist in der Handtasche', 'Impfpass', 'in der Handtasche', null],
  ['Hab das Ladekabel vom Handy in die Küchenschublade gesteckt', 'Ladekabel vom Handy', 'in der Küchenschublade', 'n'],
  ['Die Gartenschere hängt hinter der Tür im Schuppen', 'Gartenschere', 'hinter der Tür im Schuppen', 'f'],
  ['Das Sparbuch liegt bei meiner Tochter', 'Sparbuch', 'bei meiner Tochter', 'n'],
  ['Weihnachtsdeko auf den Dachboden gebracht', 'Weihnachtsdeko', 'auf dem Dachboden', null],
  ['Tabletten für die Woche neben die Kaffeemaschine gestellt', 'Tabletten für die Woche', 'neben der Kaffeemaschine', null],
  ['Ich hab den Hausschlüssel ans Schlüsselbrett gehängt', 'Hausschlüssel', 'am Schlüsselbrett', 'm'],
  ['Die Steuerunterlagen 2025 hab ich in den grünen Ordner im Keller getan', 'Steuerunterlagen 2025', 'im grünen Ordner im Keller', 'f'],
  ['Äh, also die Brille ist auf dem Klavier.', 'Brille', 'auf dem Klavier', 'f'],
  ['Oben im Schrank sind die Wolldecken', 'Wolldecken', 'oben im Schrank', 'p'],
  ['Den Pass in die Schublade hab ich getan', 'Pass', 'in der Schublade', 'm'],
  ['Ich habe den Schirm im Bus liegen lassen', 'Schirm', 'im Bus', 'm'],
  ['Geburtsurkunde in ein graues Kuvert gesteckt', 'Geburtsurkunde', 'in einem grauen Kuvert', null],
  ['Ersatzbrille ins Auto, Handschuhfach', 'Ersatzbrille', 'im Auto, Handschuhfach', null],
  ['Die Lesebrille ist im Auto', 'Lesebrille', 'im Auto', 'f']
];

for (const [satz, gegenstand, ort, genus] of faelle) {
  test(satz, () => {
    const p = zerlege(satz);
    assert.equal(p.sicher, true);
    assert.equal(p.gegenstand, gegenstand);
    assert.equal(p.ort, ort);
    assert.equal(p.genus, genus);
  });
}

const unsicher = [
  'Zweitschlüssel hat die Nachbarin',
  "Hab's in die Schublade getan",
  'Zettel für den Arzt',
  'in die schublade'
];

for (const satz of unsicher) {
  test(`unsicher: ${satz}`, () => {
    const p = zerlege(satz);
    assert.equal(p.sicher, false);
    assert.equal(p.ort, '');
    assert.equal(p.gegenstand.toLowerCase(), satz.toLowerCase());
  });
}

test('leerer Satz', () => {
  assert.equal(zerlege('').sicher, false);
  assert.equal(zerlege('   ').gegenstand, '');
});

const app = require('../app.js');

const nurOrtFaelle = [
  ['Im Küchenschrank', 'im Küchenschrank'],
  ['In die Schublade', 'in der Schublade'],
  ['In den Küchenschrank', 'im Küchenschrank'],
  ['Jetzt liegt er auf dem Kühlschrank', 'auf dem Kühlschrank'],
  ['Hab ihn in den Flurschrank getan', 'im Flurschrank'],
  ['Den Schlüssel hab ich ans Schlüsselbrett gehängt', 'am Schlüsselbrett'],
  ['Bei Oma', 'bei Oma'],
  ['Handschuhfach', 'Handschuhfach']
];

for (const [satz, ort] of nurOrtFaelle) {
  test(`nur Ort: ${satz}`, () => assert.equal(app.nurOrt(satz), ort));
}

test('Satz für umgelegten Gegenstand behält den Artikel', () => {
  const e = { gegenstand: 'Ersatzschlüssel fürs Auto', originalsatz: 'Den Ersatzschlüssel fürs Auto hab ich in die blaue Dose getan' };
  assert.equal(app.umlegeSatz(e, 'im Küchenschrank'), 'Der Ersatzschlüssel fürs Auto liegt im Küchenschrank');
  assert.equal(zerlege(app.umlegeSatz(e, 'im Küchenschrank')).genus, 'm');
  assert.equal(app.umlegeSatz({ gegenstand: 'Brille', originalsatz: 'Brille liegt auf dem Tisch' }, 'im Bad'), 'Brille liegt im Bad');
  assert.equal(app.umlegeSatz({ gegenstand: 'Winterjacken', originalsatz: 'Die Winterjacken sind im Keller' }, 'oben'), 'Die Winterjacken liegen oben');
});
