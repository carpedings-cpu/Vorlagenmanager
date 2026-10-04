/* Wo ist's? · Autorin: Diana Ziegler */
'use strict';

const CACHE = 'wo-ists-v1';
const FUSE = 'https://cdn.jsdelivr.net/npm/fuse.js@7.1.0/dist/fuse.min.js';
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

  if (req.url === FUSE) {
    ev.respondWith(caches.match(FUSE).then(treffer => treffer || fetch(req).then(r => {
      if (r.ok) caches.open(CACHE).then(c => c.put(FUSE, r.clone()));
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
