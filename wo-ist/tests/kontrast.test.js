/* Wo ist's? · Autorin: Diana Ziegler */
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const css = fs.readFileSync(path.join(__dirname, '..', 'style.css'), 'utf8');
const farbe = name => css.match(new RegExp(`--${name}:\\s*(#[0-9A-Fa-f]{6})`))[1];

function luminanz(hex) {
  const [r, g, b] = [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16) / 255)
    .map(c => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}
function kontrast(a, b) {
  const [h, d] = [luminanz(a), luminanz(b)].sort((x, y) => y - x);
  return (h + 0.05) / (d + 0.05);
}

const paare = [
  ['Text auf Grund', farbe('text'), farbe('grund')],
  ['Text auf Karte', farbe('text'), farbe('karte')],
  ['Leiser Text auf Grund', farbe('leise'), farbe('grund')],
  ['Weiß auf Grün', '#FFFFFF', farbe('gruen')],
  ['Weiß auf Blau', '#FFFFFF', farbe('blau')],
  ['Weiß auf Rot', '#FFFFFF', farbe('rot')],
  ['Link Blau auf Grund', farbe('blau'), farbe('grund')],
  ['Löschen Rot auf Karte', farbe('rot'), farbe('karte')],
  ['Meldung', farbe('text'), '#E7F0E7']
];

for (const [name, vorne, hinten] of paare) {
  test(`${name} erreicht WCAG AAA (7:1)`, () => {
    const k = kontrast(vorne, hinten);
    assert.ok(k >= 7, `${name}: ${k.toFixed(2)}:1`);
  });
}
