/* Wo ist's? · Autorin: Diana Ziegler */
'use strict';

const CACHE = 'wo-ists-v5';
const FUSE = 'https://cdn.jsdelivr.net/npm/fuse.js@7.1.0/dist/fuse.min.js';
const SUPABASE_JS = 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.117.2/dist/umd/supabase.js';
const DATEIEN = [
  './',
  'index.html',
  'app.js',
  'style.css',
  'manifest.json',
  'icons/icon-192.png',
  'icons/icon-512.png',
  'icons/icon-maskable-512.png',
  'icons/apple-touch-icon.png'
];

self.addEventListener('install', ev => {
  ev.waitUntil(
    caches.open(CACHE).then(c => Promise.all([
      c.addAll(DATEIEN),
      fetch(FUSE, { mode: 'cors' }).then(r => r.ok && c.put(FUSE, r)).catch(() => {})
    ])).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', ev => {
  ev.waitUntil(
    caches.keys()
      .then(namen => Promise.all(namen.filter(n => n !== CACHE).map(n => caches.delete(n))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', ev => {
  const req = ev.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);

  if (req.url === FUSE || req.url === SUPABASE_JS) {
    ev.respondWith(caches.match(req.url).then(treffer => treffer || fetch(req).then(r => {
      if (r.ok) caches.open(CACHE).then(c => c.put(req.url, r.clone()));
      return r;
    })));
    return;
  }

  if (url.origin !== self.location.origin) return;

  ev.respondWith(caches.open(CACHE).then(async c => {
    const treffer = await c.match(req, { ignoreSearch: true }) ||
      (req.mode === 'navigate' ? await c.match('index.html') : undefined);
    const netz = fetch(req).then(r => {
      if (r.ok && r.type === 'basic') c.put(req, r.clone());
      return r;
    }).catch(() => treffer || Response.error());
    if (treffer) {
      ev.waitUntil(netz.catch(() => {}));
      return treffer;
    }
    return netz;
  }));
});
