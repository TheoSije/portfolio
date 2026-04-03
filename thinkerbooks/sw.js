const CACHE = 'thinkerbooks-v1';
const PRECACHE = [
  './',
  './data/episodes.json',
  '../img/thinkerbooks/covers.json',
];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(PRECACHE)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys =>
    Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
  ).then(() => self.clients.claim()));
});

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  // Cache-first for images, network-first for data
  if (url.pathname.match(/\.(jpg|png|webp|svg|woff2?)$/)) {
    e.respondWith(caches.match(e.request).then(r => r || fetch(e.request).then(res => {
      const clone = res.clone();
      caches.open(CACHE).then(c => c.put(e.request, clone));
      return res;
    })));
  } else if (url.pathname.endsWith('.json')) {
    e.respondWith(fetch(e.request).catch(() => caches.match(e.request)));
  }
});
