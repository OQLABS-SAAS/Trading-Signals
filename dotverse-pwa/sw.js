// =============================================================
//  DOTVERSE - Service Worker
//  Strategy:
//    - HTML  -> network-first  (always loads latest deploy)
//    - Icons -> cache-first    (static, load instantly)
//    - API   -> bypass cache   (live data, never cached)
//
//  To force a full cache wipe on next deploy: bump CACHE_VER
// =============================================================
const CACHE_VER = 'dv-v20';
const STATIC_ASSETS = [
  '/icon-192.png',
  '/icon-512.png',
  '/apple-touch-icon.png',
];

// -- INSTALL: cache static assets, activate immediately --------
self.addEventListener('install', e => {
  self.skipWaiting();
  e.waitUntil(
    caches.open(CACHE_VER).then(c => c.addAll(STATIC_ASSETS).catch(() => {}))
  );
});

// -- ACTIVATE: delete ALL old caches, claim all open pages -----
self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(
        keys.filter(k => k !== CACHE_VER).map(k => caches.delete(k))
      ))
      .then(() => self.clients.claim())
  );
});

// Returns true for anything that should always be fresh (the app shell).
function isHtmlRequest(req, url) {
  return req.mode === 'navigate'
      || url.pathname === '/'
      || url.pathname.endsWith('.html');
}

// -- FETCH: smart routing by request type ---------------------
self.addEventListener('fetch', e => {
  const req = e.request;
  const url = new URL(req.url);

  if (req.method !== 'GET') return;
  if (url.hostname !== self.location.hostname) return;   // external APIs -> network
  if (url.pathname.startsWith('/api/')) return;          // live data -> never cached

  // HTML / app shell -> NETWORK FIRST (always latest deploy)
  if (isHtmlRequest(req, url)) {
    e.respondWith(
      fetch(req, { cache: 'no-store' })
        .then(res => {
          if (res && res.ok) {
            const clone = res.clone();
            caches.open(CACHE_VER).then(c => c.put(req, clone));
          }
          return res;
        })
        .catch(() => caches.match(req).then(c => c || caches.match('/')))
    );
    return;
  }

  // Static assets (icons, manifest) -> CACHE FIRST
  e.respondWith(
    caches.match(req).then(cached => {
      if (cached) return cached;
      return fetch(req).then(res => {
        if (res && res.ok) {
          const clone = res.clone();
          caches.open(CACHE_VER).then(c => c.put(req, clone));
        }
        return res;
      }).catch(() => new Response('', { status: 408 }));
    })
  );
});

// -- PUSH NOTIFICATIONS ----------------------------------------
self.addEventListener('push', e => {
  const data = e.data ? e.data.json() : {};
  e.waitUntil(
    self.registration.showNotification(data.title || 'DotVerse Signal', {
      body:    data.body  || 'New trading signal fired.',
      icon:    '/icon-192.png',
      badge:   '/icon-192.png',
      tag:     data.tag   || 'signal',
      data:    data.url   || '/',
      vibrate: [200, 100, 200],
    })
  );
});

self.addEventListener('notificationclick', e => {
  e.notification.close();
  e.waitUntil(clients.openWindow(e.notification.data || '/'));
});
