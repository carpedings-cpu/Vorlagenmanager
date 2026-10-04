/* Wo ist's? · Autorin: Diana Ziegler */
'use strict';

/* Gemeinsam nutzen: Projekt-URL und Publishable Key aus Supabase eintragen. Leer = nur dieses Gerät. */
const ABGLEICH = { url: '', schluessel: '' };
const SUPABASE_JS = 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.117.2/dist/umd/supabase.js';
const SUPABASE_SRI = 'sha384-Rj26LVGvoeRVR6+mwQmFfcR3QOBEwT+ZmuCWpuiqeTzJpCs0ER4ITAWGb4Hiy3Ok';

/* ---------- Satz zerlegen ---------- */

const PRAEP = new Set(['in', 'im', 'ins', 'auf', 'aufs', 'unter', 'unterm', 'unters', 'hinter', 'hinterm', 'hinters',
  'neben', 'bei', 'beim', 'zwischen', 'vor', 'vorm', 'vors', 'über', 'überm', 'übers', 'an', 'am', 'ans', 'oben', 'unten']);
const DAT_PRAEP = new Set(['in', 'auf', 'unter', 'hinter', 'neben', 'zwischen', 'vor', 'über', 'an']);
const KURZ_AKK = { ins: ['im'], ans: ['am'], aufs: ['auf', 'dem'], unters: ['unter', 'dem'], hinters: ['hinter', 'dem'],
  vors: ['vor', 'dem'], übers: ['über', 'dem'] };
const ART_AKK = { die: 'der', das: 'dem', ein: 'einem', eine: 'einer', meine: 'meiner', mein: 'meinem', deine: 'deiner',
  dein: 'deinem', seine: 'seiner', sein: 'seinem', unsere: 'unserer', unser: 'unserem' };
const ART_MASK = { den: 'dem', einen: 'einem', meinen: 'meinem', deinen: 'deinem', seinen: 'seinem', unseren: 'unserem' };
const ART_PLURAL = { die: 'den', meine: 'meinen', deine: 'deinen', seine: 'seinen', ihre: 'ihren', unsere: 'unseren' };
const GENUS = { der: 'm', den: 'm', einen: 'm', meinen: 'm', unseren: 'm', die: 'f', eine: 'f', meine: 'f', unsere: 'f', das: 'n' };
const PLURAL_VERB = new Set(['sind', 'liegen', 'stehen', 'hängen', 'befinden']);
const FUELL = new Set(['ich', 'hab', 'habe', "hab's", 'habs', 'hat', 'den', 'die', 'das', 'der', 'meine', 'meinen', 'mein',
  'unsere', 'unseren', 'unser', 'ein', 'eine', 'einen', 'also', 'so', 'äh', 'ähm', 'öhm', 'ok', 'okay', 'jetzt', 'gerade',
  'grad', 'heute', 'gestern', 'vorhin', 'eben', 'nun', 'und', 'dann', 'mal', 'da', 'hier', 'wieder', 'lege', 'leg', 'tue',
  'tu', 'stecke', 'steck', 'packe', 'pack', 'stelle', 'stell', 'hänge', 'häng', 'bringe', 'bring', 'liegt', 'liegen', 'ist',
  'sind', 'steht', 'stehen', 'hängt', 'hängen', 'befindet', 'befinden', 'sich', 'ihn', 'es']);
const ORT_ENDE = new Set([...FUELL, 'hin', 'rein', 'hinein', 'ab', 'weg', 'lassen', 'verstaut', 'versteckt', 'deponiert',
  'hinterlegt', 'aufbewahrt', 'aufgehoben', 'untergebracht', 'erstmal']);
const BEWEGUNG = new Set(['lege', 'leg', 'legen', 'tue', 'tu', 'tun', 'stecke', 'steck', 'packe', 'pack', 'stelle', 'stell',
  'hänge', 'häng', 'bringe', 'bring', 'räume', 'verstaue', 'verstaut', 'versteckt', 'verstecke', 'deponiert', 'hinterlegt',
  'untergebracht']);
const RUHE = new Set(['gelegen', 'gestanden', 'gehangen', 'gesessen', 'gewesen']);
const PARTIZIP = /^[a-zäöüß]*ge[a-zäöüß]*(t|en|tan)$/;

const sauber = w => w.replace(/^[^\p{L}\p{N}]+|[^\p{L}\p{N}]+$/gu, '');
const klein = w => sauber(w).toLowerCase();
const gross = w => /^\p{Lu}/u.test(sauber(w));
const grossAnfang = s => s ? s.charAt(0).toUpperCase() + s.slice(1) : s;
const ohneSchluss = s => s.replace(/[\s.,;:!?…]+$/u, '').trim();
const istPartizip = w => !gross(w) && PARTIZIP.test(klein(w)) && !RUHE.has(klein(w));

function ersetze(wort, neu) {
  const m = wort.match(/^([^\p{L}\p{N}]*)[\s\S]*?([^\p{L}\p{N}]*)$/u);
  return m[1] + neu + m[2];
}

function kuerze(t) {
  let a = 0, b = t.length, genus = null;
  while (a < b && FUELL.has(klein(t[a]))) { genus = genus || GENUS[klein(t[a])] || null; a++; }
  while (b > a && (FUELL.has(klein(t[b - 1])) || istPartizip(t[b - 1]))) b--;
  return { t: t.slice(a, b), genus };
}

function ortsende(t, p) {
  let i = p;
  while (i < t.length && PRAEP.has(klein(t[i]))) {
    i++;
    if (i < t.length && PRAEP.has(klein(t[i]))) continue;
    while (i < t.length && !gross(t[i])) i++;
    if (i >= t.length) return -1;
    i++;
  }
  return i < t.length ? i : -1;
}

function adjDativ(w) {
  const s = sauber(w);
  if (gross(w)) return w;
  if (/es$/.test(s)) return ersetze(w, s.slice(0, -2) + 'en');
  if (/e$/.test(s)) return ersetze(w, s + 'n');
  return w;
}

function zuDativ(ein, bewegung) {
  const t = [];
  for (const w of ein) t.push(...(KURZ_AKK[klein(w)] || [w]));
  for (let i = 0; i < t.length - 1; i++) {
    const pr = klein(t[i]);
    if (!DAT_PRAEP.has(pr)) continue;
    const art = klein(t[i + 1]);
    let j = i + 2;
    while (j < t.length && !gross(t[j]) && !PRAEP.has(klein(t[j]))) j++;
    const nomen = j < t.length && gross(t[j]) ? j : -1;
    const plural = art in ART_PLURAL && (pr === 'zwischen' || (nomen > 0 && /(en|[^s]s)$/.test(klein(t[nomen]))));
    const neu = plural ? ART_PLURAL[art]
      : pr === 'zwischen' ? null
      : ART_AKK[art] || (bewegung ? ART_MASK[art] : null);
    if (!neu) continue;
    for (let a = i + 2; a < (nomen > 0 ? nomen : j); a++) t[a] = adjDativ(t[a]);
    if (plural && nomen > 0 && !/[ns]$/.test(klein(t[nomen]))) t[nomen] = ersetze(t[nomen], sauber(t[nomen]) + 'n');
    if (neu === 'dem' && (pr === 'in' || pr === 'an')) {
      t[i] = ersetze(t[i], pr === 'in' ? 'im' : 'am');
      t.splice(i + 1, 1);
    } else {
      t[i + 1] = ersetze(t[i + 1], neu);
    }
  }
  return t;
}

function zerlege(satz) {
  const text = ohneSchluss(String(satz || '').replace(/\s+/g, ' ').trim());
  const unsicher = { gegenstand: grossAnfang(text), ort: '', sicher: false, genus: null };
  const t = text.split(' ').filter(w => sauber(w));
  const p = t.findIndex(w => PRAEP.has(klein(w)));
  if (p < 0) return unsicher;

  const bewegung = t.some(w => BEWEGUNG.has(klein(w)) || istPartizip(w));
  let ding = kuerze(t.slice(0, p)), ortT;
  if (ding.t.length) {
    ortT = t.slice(p);
  } else {
    const e = ortsende(t, p);
    if (e < 0) return unsicher;
    ortT = t.slice(p, e);
    ding = kuerze(t.slice(e));
  }
  while (ortT.length && (ORT_ENDE.has(klein(ortT[ortT.length - 1])) || istPartizip(ortT[ortT.length - 1]))) ortT.pop();

  const nurAdverb = ortT.length === 1 && ['oben', 'unten'].includes(klein(ortT[0]));
  if (!ding.t.length || ding.t.length > 8 || (ortT.length < 2 && !nurAdverb)) return unsicher;

  const ortW = zuDativ(ortT, bewegung);
  ortW[0] = ortW[0].toLowerCase();
  const plural = t.some((w, i) => PLURAL_VERB.has(klein(w)) && !/^(ge)?lassen$/.test(klein(t[i + 1] || '')));
  return {
    gegenstand: grossAnfang(ohneSchluss(ding.t.join(' '))),
    ort: ohneSchluss(ortW.join(' ')),
    sicher: true,
    genus: plural ? 'p' : ding.genus
  };
}

function nurOrt(satz) {
  const voll = zerlege(satz);
  if (voll.sicher) return voll.ort;
  const t = ohneSchluss(String(satz || '').replace(/\s+/g, ' ').trim()).split(' ').filter(w => sauber(w));
  const p = t.findIndex(w => PRAEP.has(klein(w)));
  if (p < 0) return t.join(' ');
  const ortT = t.slice(p);
  while (ortT.length > 1 && (ORT_ENDE.has(klein(ortT[ortT.length - 1])) || istPartizip(ortT[ortT.length - 1]))) ortT.pop();
  const w = zuDativ(ortT, true);
  w[0] = w[0].toLowerCase();
  return ohneSchluss(w.join(' '));
}

function umlegeSatz(e, ort) {
  const g = zerlege(e.originalsatz).genus;
  return g ? `${NOM[g]} ${e.gegenstand} ${g === 'p' ? 'liegen' : 'liegt'} ${ort}` : `${e.gegenstand} liegt ${ort}`;
}

/* ---------- Suchen ---------- */

const FRAGE_STOPP = new Set(['wo', 'wohin', 'woanders', 'ist', 'sind', 'liegt', 'liegen', 'steht', 'stehen', 'hängt', 'hängen',
  'hab', 'habe', 'hast', 'hat', 'haben', 'ich', 'du', 'er', 'sie', 'es', 'man', 'wir', 'der', 'die', 'das', 'den', 'dem', 'des',
  'mein', 'meine', 'meinen', 'meinem', 'meiner', 'unser', 'unsere', 'unseren', 'ein', 'eine', 'einen', 'denn', 'nur', 'noch',
  'nochmal', 'mal', 'eigentlich', 'bloß', 'blos', 'schon', 'wieder', 'gleich', 'bitte', 'hin', 'hingelegt', 'gelegt', 'getan',
  'gesteckt', 'gelassen', 'abgelegt', 'versteckt', 'verlegt', 'was', 'wie', 'finde', 'find', 'nicht', 'kann', 'suche', 'such',
  'sag', 'sage', 'mir', 'mich', 'weißt', 'war', 'waren', 'äh', 'ähm', 'also', 'so', 'jetzt', 'dieser', 'diese', 'dieses',
  'verflixte', 'verflixt', 'blöde', 'gibt', 'geblieben', 'gesteckt', 'gestellt', 'gepackt', 'getan']);

const normal = s => String(s || '').toLowerCase().replace(/[^\p{L}\p{N} ]+/gu, ' ').replace(/\s+/g, ' ').trim();

function frageBereinigen(frage) {
  return normal(frage).split(' ').filter(w => w.length > 1 && !FRAGE_STOPP.has(w)).join(' ');
}

function einfacheSuche(liste, q) {
  const worte = q.split(' ').filter(w => w.length >= 3);
  return liste.map(e => {
    const g = normal(e.gegenstand), s = normal(e.originalsatz);
    if (g.includes(q)) return { item: e, score: 0.05 };
    if (s.includes(q)) return { item: e, score: 0.2 };
    const n = worte.filter(w => g.includes(w) || s.includes(w)).length;
    return n ? { item: e, score: 0.4 - 0.2 * n / worte.length } : null;
  }).filter(Boolean);
}

function fuseSuche(liste, q, keys, schwelle) {
  if (typeof Fuse === 'undefined') return einfacheSuche(liste, q);
  return new Fuse(liste, { keys, includeScore: true, ignoreLocation: true, threshold: schwelle, minMatchCharLength: 3 }).search(q);
}

function laengsteGemeinsam(a, b) {
  let best = '';
  for (let i = 0; i < a.length; i++) {
    for (let j = i + best.length + 1; j <= a.length; j++) {
      if (b.includes(a.slice(i, j))) best = a.slice(i, j); else break;
    }
  }
  return best;
}

function wortteilScore(q, e) {
  const worte = normal(e.gegenstand).split(' ').filter(w => w.length >= 3);
  const gedeckt = new Array(q.length).fill(false);
  for (const qw of q.split(' ')) {
    for (const w of worte) {
      const teil = laengsteGemeinsam(qw, w);
      if (teil.length < 5 && !(teil.length >= 3 && (teil === w || teil === qw))) continue;
      const start = q.indexOf(teil);
      for (let i = start; i < start + teil.length; i++) gedeckt[i] = true;
    }
  }
  const anteil = gedeckt.filter(Boolean).length / q.replace(/ /g, '').length;
  return anteil >= 0.4 ? (1 - anteil) * 0.5 : null;
}

const SYNONYM_GRUPPEN = [
  'portemonnaie portmonee portemonee geldbörse geldbeutel brieftasche geldtasche börse',
  'handy telefon smartphone mobiltelefon iphone',
  'fernbedienung fernsteuerung',
  'brille lesebrille sehbrille',
  'schlüssel schlüsselbund',
  'ersatzschlüssel zweitschlüssel reserveschlüssel',
  'autoschlüssel fahrzeugschlüssel',
  'hausschlüssel wohnungsschlüssel haustürschlüssel',
  'ausweis personalausweis perso reisepass pass',
  'führerschein fahrerlaubnis',
  'krankenkassenkarte versichertenkarte gesundheitskarte kassenkarte',
  'bankkarte girokarte kreditkarte',
  'impfpass impfausweis',
  'tabletten medikamente pillen arznei medizin',
  'ladekabel ladegerät netzteil',
  'dokumente unterlagen papiere akten',
  'hörgerät hörgeräte hörhilfe',
  'gebiss zahnprothese prothese',
  'regenschirm schirm',
  'uhr armbanduhr',
  'kopfhörer ohrhörer',
  'tasche handtasche',
  'batterien batterie akkus',
  'taschenlampe lampe',
  'werkzeug werkzeugkasten',
  'fotos fotoalbum bilder',
  'weihnachtsdeko weihnachtssachen weihnachtsschmuck christbaumschmuck'
];
const SYNONYME = new Map();
for (const g of SYNONYM_GRUPPEN) {
  const worte = g.split(' ');
  for (const w of worte) SYNONYME.set(w, [...(SYNONYME.get(w) || []), ...worte.filter(x => x !== w)]);
}

function suche(frage, liste) {
  const q = frageBereinigen(frage);
  if (!q || !liste.length) return [];
  const exakt = liste.filter(e => normal(e.gegenstand) === q);
  if (exakt.length === 1) return exakt;
  const keys = [{ name: 'gegenstand', weight: 2 }, { name: 'originalsatz', weight: 1 }];
  const teile = new Map([q, ...q.split(' ').filter(w => w.length >= 4)].map(t => [t, 0]));
  for (const w of q.split(' ')) for (const syn of SYNONYME.get(w) || []) if (!teile.has(syn)) teile.set(syn, 0.05);
  const best = new Map();
  for (const [teil, malus] of teile) {
    for (const r of fuseSuche(liste, teil, keys, malus ? 0.25 : 0.4)) {
      const score = r.score + malus;
      const alt = best.get(r.item.id);
      if (!alt || score < alt.score) best.set(r.item.id, { item: r.item, score });
    }
  }
  for (const e of liste) {
    const score = wortteilScore(q, e);
    const alt = best.get(e.id);
    if (score != null && (!alt || score < alt.score)) best.set(e.id, { item: e, score });
  }
  const sortiert = [...best.values()].sort((a, b) => a.score - b.score);
  if (!sortiert.length) return [];
  const grenze = sortiert[0].score + 0.1;
  return sortiert.filter(r => r.score <= grenze).slice(0, 3).map(r => r.item);
}

function findeDoppelt(gegenstand, liste) {
  const q = normal(gegenstand);
  if (!q || !liste.length) return null;
  const gleich = liste.find(e => normal(e.gegenstand) === q) ||
    liste.find(e => (SYNONYME.get(q) || []).includes(normal(e.gegenstand)));
  if (gleich) return gleich;
  const r = fuseSuche(liste, q, ['gegenstand'], 0.3)[0];
  const laenge = r ? Math.min(q.length, normal(r.item.gegenstand).length) / Math.max(q.length, normal(r.item.gegenstand).length) : 0;
  return r && r.score <= 0.2 && laenge >= 0.5 ? r.item : null;
}

/* ---------- Sätze für Anzeige und Sprache ---------- */

const NOM = { m: 'Der', f: 'Die', n: 'Das', p: 'Die' };
const AKK = { m: 'den', f: 'die', n: 'das', p: 'die' };
const VORHER = { m: 'Vorher lag er:', f: 'Vorher lag sie:', n: 'Vorher lag es:', p: 'Vorher lagen sie:' };

const genusVon = e => zerlege(e.originalsatz).genus;
const anzeigeName = e => e.ort ? e.gegenstand : ohneSchluss(e.originalsatz);

function antwortSatz(e) {
  if (!e.ort) return ohneSchluss(e.originalsatz) + '.';
  const g = genusVon(e);
  return g ? `${NOM[g]} ${e.gegenstand} ${g === 'p' ? 'sind' : 'ist'} ${e.ort}.` : `${e.gegenstand}: ${e.ort}.`;
}

function rueckfrage(alt, genus) {
  const g = genusVon(alt) || genus;
  return g ? `Meinen Sie ${AKK[g]} ${alt.gegenstand} von vorher?` : `Meinen Sie diesen Eintrag von vorher: ${anzeigeName(alt)}?`;
}

function vorherSatz(e, v) {
  return `${VORHER[genusVon(e)] || 'Vorher:'} ${v.ort} (${datum(v.datum)})`;
}

function datum(iso) {
  const d = new Date(iso);
  return isNaN(d) ? '' : d.toLocaleDateString('de-DE', { day: 'numeric', month: 'long', year: 'numeric' });
}

if (typeof module === 'object' && module.exports) {
  module.exports = { zerlege, nurOrt, umlegeSatz, frageBereinigen, suche, findeDoppelt, antwortSatz, rueckfrage, vorherSatz };
}

/* ---------- Speicher (IndexedDB) ---------- */

let dbVersprechen;
function db() {
  return dbVersprechen ||= new Promise((ok, fehler) => {
    const r = indexedDB.open('wo-ists', 1);
    r.onupgradeneeded = () => r.result.createObjectStore('eintraege', { keyPath: 'id' });
    r.onsuccess = () => ok(r.result);
    r.onerror = () => fehler(r.error);
  });
}

async function tx(modus, fn) {
  const d = await db();
  return new Promise((ok, fehler) => {
    const t = d.transaction('eintraege', modus);
    const r = fn(t.objectStore('eintraege'));
    t.oncomplete = () => ok(r.result);
    t.onerror = () => fehler(t.error);
  });
}

const alleRoh = () => tx('readonly', s => s.getAll());
const alle = async () => (await alleRoh()).filter(e => !e.geloescht);
const hole = id => tx('readonly', s => s.get(id));
const lege = e => tx('readwrite', s => s.put(e));
const entferne = id => tx('readwrite', s => s.delete(id));

const fotoAblegen = async blob => ({ typ: blob.type || 'image/jpeg', daten: await blob.arrayBuffer() });
const fotoBlob = f => !f ? null : f instanceof Blob ? f : new Blob([f.daten], { type: f.typ });

function ausDataUrl(url) {
  const [kopf, b64] = url.split(',');
  const bytes = Uint8Array.from(atob(b64), z => z.charCodeAt(0));
  return new Blob([bytes], { type: kopf.slice(5, kopf.indexOf(';')) });
}

const neueId = () => (crypto.randomUUID ? crypto.randomUUID() : Date.now().toString(36) + Math.random().toString(36).slice(2));

/* ---------- Oberfläche ---------- */

if (typeof document !== 'undefined') start();

function start() {
  const $ = s => document.querySelector(s);
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  const IOS = /iPad|iPhone|iPod/.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  const STANDALONE = matchMedia('(display-mode: standalone)').matches || navigator.standalone === true;
  const GRUND = {
    'not-allowed': 'Das Mikrofon ist für diese App nicht freigegeben.',
    'service-not-allowed': 'Die Spracherkennung ist hier nicht verfügbar.',
    'audio-capture': 'Ich finde kein Mikrofon.',
    'network': 'Die Spracherkennung braucht gerade Internet.',
    'language-not-supported': 'Die Spracherkennung kann hier kein Deutsch.'
  };

  let hoerenGeht = !!SR && !(IOS && STANDALONE);
  let modus = 'ablegen', erkennung = null, letzter = null, offen = null, audio = null, stimme = null, entsperrt = false;
  let zuLoeschen = null, fotoUrl = null, trefferUrl = null, umlegen = null;
  let sb = null, sitzung = null, abgleichTimer = null, gleichtAb = false, nochmalAbgleichen = false;

  const el = (tag, klasse, text) => {
    const n = document.createElement(tag);
    if (klasse) n.className = klasse;
    if (text != null) n.textContent = text;
    return n;
  };
  const leere = s => { const n = $(s); n.replaceChildren(); return n; };

  document.documentElement.dataset.hoeren = hoerenGeht ? 'ja' : 'nein';

  /* Sprache und Töne */

  function waehleStimme() {
    const de = speechSynthesis.getVoices().filter(v => /^de/i.test(v.lang));
    stimme = de.find(v => v.lang === 'de-DE' && v.localService) || de.find(v => v.lang === 'de-DE') || de[0] || null;
  }

  function sage(text) {
    if (!('speechSynthesis' in window)) return;
    speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.lang = 'de-DE';
    u.rate = 0.9;
    if (stimme) u.voice = stimme;
    speechSynthesis.speak(u);
  }

  function entsperre() {
    if (entsperrt) return;
    entsperrt = true;
    if ('speechSynthesis' in window) {
      const u = new SpeechSynthesisUtterance(' ');
      u.volume = 0;
      speechSynthesis.speak(u);
    }
    ton(0, 1);
  }

  function ton(hz = 660, ms = 160) {
    try {
      audio ||= new (window.AudioContext || window.webkitAudioContext)();
      if (audio.state === 'suspended') audio.resume();
      if (!hz) return;
      const o = audio.createOscillator(), g = audio.createGain(), t = audio.currentTime;
      o.frequency.value = hz;
      g.gain.setValueAtTime(0.0001, t);
      g.gain.exponentialRampToValueAtTime(0.25, t + 0.02);
      g.gain.exponentialRampToValueAtTime(0.0001, t + ms / 1000);
      o.connect(g).connect(audio.destination);
      o.start(t);
      o.stop(t + ms / 1000 + 0.05);
    } catch (_) { /* ohne Ton weiter */ }
  }

  /* Bildschirme */

  const merke = {
    lies: k => { try { return localStorage.getItem('woists.' + k); } catch (_) { return null; } },
    setze: (k, v) => { try { localStorage.setItem('woists.' + k, v); } catch (_) { /* ohne Merker weiter */ } }
  };

  function pruefeErinnerung() {
    const seit = Number(merke.lies('seit')) || 0;
    const bezug = Date.parse(merke.lies('bezug') || '') || Date.now();
    const spaeter = Date.parse(merke.lies('spaeter') || '') || 0;
    const faellig = seit > 0 && Date.now() >= spaeter && (seit >= 20 || Date.now() - bezug >= 30 * 864e5);
    $('#erinnerung').hidden = !faellig;
  }

  function gesichert() {
    merke.setze('seit', '0');
    merke.setze('bezug', new Date().toISOString());
    $('#erinnerung').hidden = true;
  }

  function zeige(name) {
    if (name === 'start') pruefeErinnerung();
    document.querySelectorAll('.screen').forEach(s => { s.hidden = s.id !== 's-' + name; });
    if (name !== 'start' && !(history.state && history.state.tief)) history.pushState({ tief: true }, '');
    window.scrollTo(0, 0);
    const ziel = $('#s-' + name + ' [data-fokus]');
    if (ziel) ziel.focus({ preventScroll: true });
  }

  function zumStart() {
    stoppeHoeren();
    if (history.state && history.state.tief) history.back();
    else zeige('start');
  }

  window.addEventListener('popstate', () => {
    if (history.state && history.state.tief) return;
    stoppeHoeren();
    zeige('start');
  });

  /* Hören und Tippen */

  function starte(m) {
    modus = m;
    entsperre();
    if ('speechSynthesis' in window) speechSynthesis.cancel();
    const titel = { ablegen: 'Was legen Sie wohin?', suchen: 'Was suchen Sie?' };
    const beispiel = {
      ablegen: 'Zum Beispiel: „Die Brille liegt auf dem Nachttisch.“',
      suchen: 'Zum Beispiel: „Wo ist meine Brille?“',
      umlegen: 'Zum Beispiel: „Im Küchenschrank.“'
    };
    if (m === 'umlegen') {
      const g = genusVon(umlegen);
      titel.umlegen = g
        ? `Wo ${g === 'p' ? 'liegen' : 'liegt'} ${NOM[g].toLowerCase()} ${umlegen.gegenstand} jetzt?`
        : `Wo liegt ${umlegen.gegenstand} jetzt?`;
    }
    $('#hoeren-titel').textContent = $('#tippen-titel').textContent = titel[m];
    $('#hoeren-beispiel').textContent = $('#tippen-beispiel').textContent = beispiel[m];
    document.body.dataset.modus = m;
    if (hoerenGeht) hoere(); else tippen();
  }

  function hoere() {
    stoppeHoeren();
    const r = new SR();
    erkennung = r;
    r.lang = 'de-DE';
    r.interimResults = true;
    r.continuous = false;
    r.maxAlternatives = 1;
    let text = '', fehler = null;
    const notbremse = setTimeout(() => { try { r.stop(); } catch (_) { /* schon beendet */ } }, 20000);
    r.onresult = ev => {
      text = Array.from(ev.results).map(x => x[0].transcript).join(' ').trim();
      $('#hoeren-text').textContent = text;
    };
    r.onerror = ev => { fehler = ev.error; };
    r.onend = () => {
      clearTimeout(notbremse);
      if (erkennung !== r) return;
      erkennung = null;
      ton(440);
      if (fehler && GRUND[fehler]) {
        if (fehler !== 'network') hoerenGeht = false;
        return tippen(GRUND[fehler]);
      }
      if (text) verarbeite(text);
      else { zeige('nichts'); sage('Ich habe nichts gehört. Bitte noch einmal.'); }
    };
    $('#hoeren-text').textContent = '';
    zeige('hoeren');
    try { r.start(); ton(880); } catch (_) { erkennung = null; tippen(); }
  }

  function stoppeHoeren() {
    if (!erkennung) return;
    const r = erkennung;
    erkennung = null;
    try { r.abort(); } catch (_) { /* schon beendet */ }
  }

  function tippen(grund) {
    stoppeHoeren();
    const g = $('#tippen-grund');
    g.textContent = grund ? grund + ' Sie können stattdessen tippen.' : '';
    g.hidden = !grund;
    $('#eingabe').value = '';
    zeige('tippen');
    ton(660);
    if (grund) sage(grund + ' Sie können stattdessen tippen.');
  }

  function verarbeite(text) {
    if (modus === 'umlegen') return woanders(text);
    return modus === 'ablegen' ? ablegen(text) : finde(text);
  }

  /* Ablegen */

  async function ablegen(text) {
    const p = zerlege(text);
    const alt = p.sicher ? findeDoppelt(p.gegenstand, await alle()) : null;
    if (!alt) return speichere(p, text, null);
    offen = { p, text, alt };
    const frage = rueckfrage(alt, p.genus);
    $('#frage-text').textContent = frage;
    $('#frage-bisher').textContent = 'Bisher: ' + (alt.ort || ohneSchluss(alt.originalsatz));
    zeige('frage');
    sage(frage);
  }

  async function woanders(text) {
    const e = await hole(umlegen.id);
    if (!e) return ablegen(text);
    const ort = nurOrt(text);
    return speichere({ gegenstand: e.gegenstand, ort, sicher: true }, umlegeSatz(e, ort), e);
  }

  async function aendere(e) {
    e.geaendert = new Date().toISOString();
    e.offen = true;
    await lege(e);
    planeAbgleich();
  }

  async function loescheEintrag(id) {
    const e = await hole(id);
    if (!e) return;
    if (!sitzung) return entferne(id);
    await aendere({ ...e, geloescht: true, foto: null, fotoPfad: null, fotoAlt: [...(e.fotoAlt || []), e.fotoPfad].filter(Boolean) });
  }

  async function speichere(p, text, alt) {
    const jetzt = new Date().toISOString();
    const e = alt
      ? {
          ...alt,
          gegenstand: p.gegenstand.length > alt.gegenstand.length ? p.gegenstand : alt.gegenstand,
          ort: p.ort,
          originalsatz: text,
          foto: null,
          fotoPfad: null,
          fotoAlt: [...(alt.fotoAlt || []), alt.fotoPfad].filter(Boolean),
          erstellt: jetzt,
          verlauf: [{ ort: alt.ort || ohneSchluss(alt.originalsatz), datum: alt.erstellt }, ...(alt.verlauf || [])].slice(0, 10)
        }
      : { id: neueId(), gegenstand: p.gegenstand, ort: p.ort, originalsatz: text, foto: null, erstellt: jetzt, verlauf: [] };
    await aendere(e);
    merke.setze('seit', String((Number(merke.lies('seit')) || 0) + 1));
    if (!merke.lies('bezug')) merke.setze('bezug', jetzt);
    if (navigator.storage && navigator.storage.persist) navigator.storage.persist().catch(() => {});
    letzter = { id: e.id, vorher: alt };
    const satz = 'Gespeichert: ' + (p.sicher ? `${e.gegenstand}, ${e.ort}` : ohneSchluss(text));
    $('#ok-text').textContent = satz;
    $('#ok-hinweis').hidden = p.sicher;
    zeigeFoto(null);
    $('#b-foto').textContent = 'Foto vom Ort';
    zeige('ok');
    ton(990, 200);
    sage(satz);
  }

  function zeigeFoto(blob) {
    const img = $('#ok-foto');
    if (fotoUrl) URL.revokeObjectURL(fotoUrl);
    fotoUrl = blob ? URL.createObjectURL(blob) : null;
    img.hidden = !blob;
    if (blob) img.src = fotoUrl; else img.removeAttribute('src');
  }

  async function nochmal() {
    if (letzter) {
      if (letzter.vorher) await aendere({ ...letzter.vorher });
      else await loescheEintrag(letzter.id);
      letzter = null;
    }
    starte(modus === 'umlegen' ? 'umlegen' : 'ablegen');
  }

  function ladeBild(datei) {
    return new Promise((ok, fehler) => {
      const url = URL.createObjectURL(datei);
      const img = new Image();
      img.onload = () => { URL.revokeObjectURL(url); ok(img); };
      img.onerror = () => { URL.revokeObjectURL(url); fehler(new Error('Bild')); };
      img.src = url;
    });
  }

  async function verkleinere(datei) {
    const img = await ladeBild(datei);
    const f = Math.min(1, 1200 / img.naturalWidth);
    const c = document.createElement('canvas');
    c.width = Math.round(img.naturalWidth * f);
    c.height = Math.round(img.naturalHeight * f);
    c.getContext('2d').drawImage(img, 0, 0, c.width, c.height);
    return new Promise(ok => c.toBlob(ok, 'image/jpeg', 0.7));
  }

  async function fotoGewaehlt(datei) {
    if (!datei || !letzter) return;
    try {
      const blob = await verkleinere(datei);
      const e = await hole(letzter.id);
      e.fotoAlt = [...(e.fotoAlt || []), e.fotoPfad].filter(Boolean);
      e.foto = await fotoAblegen(blob);
      e.fotoPfad = null;
      await aendere(e);
      zeigeFoto(blob);
      $('#b-foto').textContent = 'Anderes Foto';
      ton(990, 200);
      sage('Foto gespeichert.');
    } catch (_) {
      sage('Das Foto hat leider nicht geklappt.');
    }
  }

  /* Suchen */

  async function finde(text) {
    const treffer = suche(text, await alle());
    $('#frage-echo').textContent = `Ihre Frage: „${ohneSchluss(text)}“`;
    if (!treffer.length) {
      leere('#treffer').append(el('p', 'ergebnis', 'Dazu habe ich nichts gespeichert.'));
      zeige('treffer');
      ton(330, 250);
      sage('Dazu habe ich nichts gespeichert.');
    } else if (treffer.length === 1) {
      zeigeTreffer(treffer[0]);
    } else {
      const box = leere('#treffer');
      box.append(el('p', 'ergebnis', 'Ich habe mehrere Einträge gefunden. Welchen meinen Sie?'));
      for (const e of treffer) {
        const b = el('button', 'karte wahl');
        b.type = 'button';
        b.append(el('span', 'ding', anzeigeName(e)));
        if (e.ort) b.append(el('span', 'ort', grossAnfang(e.ort)));
        b.addEventListener('click', () => zeigeTreffer(e));
        box.append(b);
      }
      zeige('treffer');
      ton(660);
      sage(`Ich habe mehrere Einträge gefunden: ${treffer.map(anzeigeName).join(', oder ')}. Welchen meinen Sie?`);
    }
  }

  function zeigeTreffer(e) {
    const box = leere('#treffer');
    const k = el('article', 'karte');
    k.append(el('p', 'ding', anzeigeName(e)));
    if (e.ort) k.append(el('p', 'ort', grossAnfang(e.ort)));
    if (trefferUrl) URL.revokeObjectURL(trefferUrl);
    trefferUrl = e.foto ? URL.createObjectURL(fotoBlob(e.foto)) : null;
    if (trefferUrl) {
      const img = el('img', 'foto');
      img.alt = 'Foto vom Ort';
      img.src = trefferUrl;
      k.append(img);
    }
    k.append(el('p', 'klein', 'Gespeichert am ' + datum(e.erstellt)));
    if (e.verlauf && e.verlauf[0]) k.append(el('p', 'klein', vorherSatz(e, e.verlauf[0])));
    box.append(k);
    const vorlesen = el('button', 'knopf hell', 'Nochmal vorlesen');
    vorlesen.type = 'button';
    vorlesen.addEventListener('click', () => { ton(660, 80); sage(antwortSatz(e)); });
    box.append(vorlesen);
    if (e.ort) {
      const weiter = el('button', 'knopf gruen', 'Liegt jetzt woanders');
      weiter.type = 'button';
      weiter.addEventListener('click', () => { umlegen = e; starte('umlegen'); });
      box.append(weiter);
    }
    zeige('treffer');
    ton(990, 200);
    sage(antwortSatz(e));
  }

  /* Alle Einträge */

  async function zeigeListe(meldung, leise) {
    const liste = (await alle()).sort((a, b) => anzeigeName(a).localeCompare(anzeigeName(b), 'de'));
    const ul = leere('#liste');
    for (const e of liste) {
      const li = el('li', 'karte');
      li.append(el('p', 'ding', anzeigeName(e)));
      if (e.ort) li.append(el('p', 'ort-klein', grossAnfang(e.ort)));
      li.append(el('p', 'klein', 'Gespeichert am ' + datum(e.erstellt) + (e.foto ? ' · mit Foto' : '')));
      const b = el('button', 'knopf loeschen', 'Löschen');
      b.type = 'button';
      b.addEventListener('click', () => frageLoeschen(e));
      li.append(b);
      ul.append(li);
    }
    const anzahl = liste.length === 0 ? 'Noch keine Einträge gespeichert.'
      : liste.length === 1 ? 'Ein Eintrag gespeichert.' : `${liste.length} Einträge gespeichert.`;
    $('#liste-anzahl').textContent = anzahl;
    if (leise) return;
    melde(meldung || '');
    zeige('liste');
    if (!meldung) sage(anzahl);
  }

  function melde(text) {
    const m = $('#liste-meldung');
    m.textContent = text;
    m.hidden = !text;
    if (text) sage(text);
  }

  function frageLoeschen(e) {
    zuLoeschen = e;
    const frage = `Wirklich löschen: ${anzeigeName(e)}?`;
    $('#loeschen-text').textContent = frage;
    zeige('loeschen');
    sage(frage);
  }

  async function loeschen() {
    if (!zuLoeschen) return;
    await loescheEintrag(zuLoeschen.id);
    zuLoeschen = null;
    ton(440);
    zeigeListe('Gelöscht.');
  }

  /* Datensicherung */

  const alsDataUrl = blob => new Promise((ok, fehler) => {
    const r = new FileReader();
    r.onload = () => ok(r.result);
    r.onerror = () => fehler(r.error);
    r.readAsDataURL(blob);
  });

  async function sichern() {
    const liste = await alle();
    const daten = {
      app: "Wo ist's?",
      autorin: 'Diana Ziegler',
      version: 1,
      exportiert: new Date().toISOString(),
      eintraege: await Promise.all(liste.map(async e => ({
        id: e.id,
        gegenstand: e.gegenstand,
        ort: e.ort,
        originalsatz: e.originalsatz,
        foto: e.foto ? await alsDataUrl(fotoBlob(e.foto)) : null,
        erstellt: e.erstellt,
        verlauf: e.verlauf || []
      })))
    };
    const name = `wo-ists-sicherung-${new Date().toISOString().slice(0, 10)}.json`;
    const datei = new File([JSON.stringify(daten)], name, { type: 'application/json' });
    if (navigator.canShare && navigator.canShare({ files: [datei] })) {
      try {
        await navigator.share({ files: [datei], title: "Wo ist's? Sicherung" });
        gesichert();
        return melde('Sicherung erstellt.');
      } catch (err) {
        if (err.name === 'AbortError') return melde('Sicherung abgebrochen.');
      }
    }
    const a = el('a');
    a.href = URL.createObjectURL(datei);
    a.download = name;
    document.body.append(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 5000);
    gesichert();
    melde(`Sicherung gespeichert: ${liste.length === 1 ? 'ein Eintrag' : liste.length + ' Einträge'}.`);
  }

  async function laden(datei) {
    if (!datei) return;
    try {
      const d = JSON.parse(await datei.text());
      const roh = Array.isArray(d) ? d : d && d.eintraege;
      if (!Array.isArray(roh)) throw new Error('Format');
      let n = 0;
      for (const x of roh) {
        if (!x || !x.id || typeof x.originalsatz !== 'string') continue;
        const foto = typeof x.foto === 'string' && /^data:image\/(jpeg|png|webp);base64,/.test(x.foto)
          ? await fotoAblegen(ausDataUrl(x.foto)) : null;
        await aendere({
          id: String(x.id),
          gegenstand: String(x.gegenstand || ''),
          ort: String(x.ort || ''),
          originalsatz: x.originalsatz,
          foto,
          erstellt: x.erstellt || new Date().toISOString(),
          verlauf: Array.isArray(x.verlauf)
            ? x.verlauf.filter(v => v && v.ort).map(v => ({ ort: String(v.ort), datum: v.datum || null })) : []
        });
        n++;
      }
      zeigeListe(n === 1 ? 'Ein Eintrag geladen.' : `${n} Einträge geladen.`);
    } catch (_) {
      melde('Diese Datei kann ich nicht lesen.');
    }
  }

  /* Gemeinsam nutzen (Supabase) */

  const konfig = window.WOISTS_ABGLEICH || ABGLEICH;

  function ladeSkript(src, sri) {
    return new Promise((ok, fehler) => {
      const s = document.createElement('script');
      s.src = src;
      s.integrity = sri;
      s.crossOrigin = 'anonymous';
      s.onload = ok;
      s.onerror = fehler;
      document.head.append(s);
    });
  }

  function teilenMeldung(text, sprechen = true) {
    const m = $('#teilen-meldung');
    m.textContent = text;
    m.hidden = !text;
    if (text && sprechen) sage(text);
  }

  function zeigeTeilen() {
    $('#teilen-aus').hidden = !!sitzung;
    $('#teilen-an').hidden = !sitzung;
    if (sitzung) $('#teilen-wer').textContent = `Verbunden als ${sitzung.user.email}.`;
    $('#sicherung-text').textContent = sitzung
      ? 'Die Einträge liegen auf diesem Gerät und im gemeinsamen Konto. Eine zusätzliche Sicherung schadet trotzdem nicht.'
      : 'Die Einträge liegen nur auf diesem Gerät. Speichern Sie ab und zu eine Sicherung, zum Beispiel in Ihren Dateien oder per E-Mail an sich selbst.';
  }

  async function verbinde() {
    if (!konfig.url) return;
    $('#teilen').hidden = false;
    try {
      if (!window.supabase) await ladeSkript(SUPABASE_JS, SUPABASE_SRI);
      sb = window.supabase.createClient(konfig.url, konfig.schluessel);
      sitzung = (await sb.auth.getSession()).data.session;
    } catch (_) {
      teilenMeldung('Ohne Internet kann ich mich gerade nicht verbinden.', false);
      return;
    }
    zeigeTeilen();
    if (sitzung) gleicheAb();
  }

  function planeAbgleich() {
    if (!sitzung) return;
    clearTimeout(abgleichTimer);
    abgleichTimer = setTimeout(gleicheAb, 1500);
  }

  async function uebernimm(z, lokal) {
    if (z.geloescht) {
      if (lokal) await entferne(z.id);
      return true;
    }
    let foto = lokal && lokal.fotoPfad === z.foto_pfad ? lokal.foto : null;
    let geklappt = true;
    if (z.foto_pfad && !foto) {
      const { data, error } = await sb.storage.from('fotos').download(z.foto_pfad);
      if (!error && data) foto = await fotoAblegen(data); else geklappt = false;
    }
    await lege({
      id: z.id,
      gegenstand: z.gegenstand,
      ort: z.ort,
      originalsatz: z.originalsatz,
      foto,
      fotoPfad: foto ? z.foto_pfad : null,
      erstellt: z.erstellt,
      verlauf: z.verlauf || [],
      geaendert: z.geaendert,
      offen: false
    });
    return geklappt;
  }

  async function schiebe(e) {
    const fotos = sb.storage.from('fotos');
    let pfad = e.fotoPfad || null;
    if (e.foto && !pfad && !e.geloescht) {
      pfad = `${sitzung.user.id}/${e.id}/${Date.now()}.jpg`;
      const { error } = await fotos.upload(pfad, fotoBlob(e.foto), { contentType: 'image/jpeg', upsert: true });
      if (error) throw error;
    }
    const { error } = await sb.from('eintraege').upsert({
      id: e.id,
      gegenstand: e.gegenstand,
      ort: e.ort,
      originalsatz: e.originalsatz,
      foto_pfad: e.geloescht ? null : pfad,
      erstellt: e.erstellt,
      verlauf: e.verlauf || [],
      geaendert: e.geaendert,
      geloescht: !!e.geloescht
    });
    if (error) throw error;
    if (e.fotoAlt && e.fotoAlt.length) await fotos.remove(e.fotoAlt).catch(() => {});
    const jetzt = await hole(e.id);
    if (!jetzt || jetzt.geaendert !== e.geaendert) return;
    if (e.geloescht) await entferne(e.id);
    else await lege({ ...jetzt, fotoPfad: pfad, fotoAlt: [], offen: false });
  }

  async function gleicheAb() {
    if (!sb || !sitzung) return;
    if (gleichtAb) { nochmalAbgleichen = true; return; }
    gleichtAb = true;
    document.documentElement.dataset.abgleich = 'laeuft';
    $('#teilen-stand').textContent = 'Gleiche gerade ab …';
    try {
      const cursor = merke.lies('abgleich') || '1970-01-01T00:00:00.000Z';
      const ab = new Date(Date.parse(cursor) - 5 * 60e3).toISOString();
      const { data: zeilen, error } = await sb.from('eintraege').select('*').gt('server_zeit', ab).order('server_zeit');
      if (error) throw error;
      let neuster = Date.parse(cursor), vollstaendig = true, geaendert = false;
      for (const z of zeilen || []) {
        neuster = Math.max(neuster, Date.parse(z.server_zeit));
        const lokal = await hole(z.id);
        if (lokal && lokal.offen && Date.parse(lokal.geaendert) >= Date.parse(z.geaendert)) continue;
        if (lokal && !lokal.offen && Date.parse(lokal.geaendert) === Date.parse(z.geaendert) && lokal.fotoPfad === (z.foto_pfad || null)) continue;
        if (!(await uebernimm(z, lokal))) vollstaendig = false;
        geaendert = true;
      }
      for (const e of (await alleRoh()).filter(x => x.offen)) await schiebe(e);
      if (vollstaendig) merke.setze('abgleich', new Date(neuster).toISOString());
      const uhr = new Date().toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' });
      $('#teilen-stand').textContent = `Zuletzt abgeglichen um ${uhr} Uhr.`;
      document.documentElement.dataset.abgleich = 'fertig';
      gesichert();
      if (geaendert && !$('#s-liste').hidden) zeigeListe(null, true);
    } catch (_) {
      $('#teilen-stand').textContent = 'Abgleich hat nicht geklappt. Ich versuche es später noch einmal.';
      document.documentElement.dataset.abgleich = 'fehler';
    } finally {
      document.documentElement.dataset.abgleichNr = String((Number(document.documentElement.dataset.abgleichNr) || 0) + 1);
      gleichtAb = false;
      if (nochmalAbgleichen) { nochmalAbgleichen = false; gleicheAb(); }
    }
  }

  const ANMELDE_FEHLER = {
    'Invalid login credentials': 'E-Mail oder Passwort stimmt nicht.',
    'Email not confirmed': 'Die E-Mail ist noch nicht bestätigt. Bitte den Link in der E-Mail antippen.',
    'User already registered': 'Für diese E-Mail gibt es schon ein Konto. Bitte anmelden.'
  };

  async function anmelden(neu) {
    if (!sb) return teilenMeldung('Ohne Internet kann ich mich gerade nicht verbinden.');
    const email = $('#teilen-mail').value.trim();
    const password = $('#teilen-pw').value;
    if (!email || !password) return teilenMeldung('Bitte E-Mail und Passwort eingeben.');
    if (neu && password.length < 8) return teilenMeldung('Das Passwort braucht mindestens 8 Zeichen.');
    teilenMeldung('Einen Moment …', false);
    try {
      const { data, error } = neu
        ? await sb.auth.signUp({ email, password })
        : await sb.auth.signInWithPassword({ email, password });
      if (error) return teilenMeldung(ANMELDE_FEHLER[error.message] || 'Das hat nicht geklappt. Bitte später noch einmal versuchen.');
      if (!data.session) return teilenMeldung('Ich habe Ihnen eine E-Mail geschickt. Bitte den Link darin antippen und sich danach hier anmelden.');
      sitzung = data.session;
    } catch (_) {
      return teilenMeldung('Ohne Internet kann ich mich gerade nicht anmelden.');
    }
    $('#teilen-pw').value = '';
    merke.setze('abgleich', '');
    for (const e of await alleRoh()) if (!e.offen) await lege({ ...e, offen: true, geaendert: e.geaendert || e.erstellt });
    zeigeTeilen();
    ton(990, 200);
    teilenMeldung('Angemeldet. Ich gleiche jetzt mit dem anderen Gerät ab.');
    gleicheAb();
  }

  async function abmelden() {
    if (sb) await sb.auth.signOut().catch(() => {});
    sitzung = null;
    merke.setze('abgleich', '');
    zeigeTeilen();
    ton(440);
    teilenMeldung('Abgemeldet. Die Einträge bleiben auf diesem Gerät.');
  }

  /* Knöpfe */

  const klick = (s, fn) => $(s).addEventListener('click', fn);
  klick('#b-ablegen', () => starte('ablegen'));
  klick('#b-erinnerung-ja', () => { entsperre(); sichern(); });
  klick('#b-erinnerung-spaeter', () => {
    merke.setze('spaeter', new Date(Date.now() + 7 * 864e5).toISOString());
    $('#erinnerung').hidden = true;
    ton(660, 80);
    sage('In Ordnung. Ich erinnere Sie in einer Woche.');
  });
  klick('#b-suchen', () => starte('suchen'));
  klick('#b-liste', () => { entsperre(); zeigeListe(); });
  klick('#b-fertig', () => {
    const text = $('#eingabe').value.trim();
    if (!text) { sage('Bitte erst etwas eingeben.'); $('#eingabe').focus(); return; }
    ton(440);
    verarbeite(text);
  });
  klick('#b-ja', () => { if (offen) speichere(offen.p, offen.text, offen.alt); offen = null; });
  klick('#b-nein', () => { if (offen) speichere(offen.p, offen.text, null); offen = null; });
  klick('#b-stimmt', () => { ton(990, 120); sage('Alles klar.'); zumStart(); });
  klick('#b-nochmal', nochmal);
  klick('#b-foto', () => $('#foto-input').click());
  $('#foto-input').addEventListener('change', ev => { fotoGewaehlt(ev.target.files[0]); ev.target.value = ''; });
  klick('#b-loeschen-ja', loeschen);
  klick('#b-export', sichern);
  klick('#b-import', () => $('#import-input').click());
  klick('#b-anmelden', () => anmelden(false));
  klick('#b-registrieren', () => anmelden(true));
  klick('#b-abgleichen', () => { ton(660, 80); sage('Ich gleiche ab.'); gleicheAb(); });
  klick('#b-abmelden', abmelden);
  window.addEventListener('online', () => gleicheAb());
  document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'visible') gleicheAb(); });
  $('#import-input').addEventListener('change', ev => { laden(ev.target.files[0]); ev.target.value = ''; });

  document.addEventListener('click', ev => {
    const b = ev.target.closest('[data-aktion]');
    if (!b) return;
    const a = b.dataset.aktion;
    if (a === 'start') zumStart();
    else if (a === 'tippen') tippen();
    else if (a === 'nochmal') starte(modus);
    else if (a === 'suchen') starte('suchen');
    else if (a === 'liste') zeigeListe();
  });

  pruefeErinnerung();
  verbinde();

  if ('speechSynthesis' in window) {
    waehleStimme();
    speechSynthesis.addEventListener('voiceschanged', waehleStimme);
  }

  if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => navigator.serviceWorker.register('service-worker.js').catch(() => {}));
  }
}
