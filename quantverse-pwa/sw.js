// ─────────────────────────────────────────────────────────────
//  QUANT VERSE — Service Worker
//  Strategy:
//    • HTML  → network-first  (always loads latest deploy)
//    • Icons → cache-first    (static, load instantly)
//    • API   → bypass cache   (live Binance data, never cached)
//
//  To force a full cache wipe on next deploy: bump CACHE_VER
// ─────────────────────────────────────────────────────────────
const CACHE_VER = 'qv-v5';
const STATIC_ASSETS = [
  '/icon-192.png',
  '/icon-512.png',
  '/apple-touch-icon.png',
];

// ── INSTALL: cache static assets, activate immediately ───────
self.addEventListener('install', e => {
  self.skipWaiting(); // Don't wait — activate right away
  e.waitUntil(
    caches.open(CACHE_VER).then(c => c.addAll(STATIC_ASSETS).catch(()=>{}))
  );
});

// ── ACTIVATE: delete old caches, claim all open pages ────────
self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(
        keys.filter(k => k !== CACHE_VER).map(k => {
          console.log('[QV SW] Deleting old cache:', k);
          return caches.delete(k);
        })
      ))
      .then(() => self.clients.claim()) // Take control of all tabs immediately
  );
});

// ── FETCH: smart routing by request type ─────────────────────
self.addEventListener('fetch', e => {
  const req = e.request;
  const url = new URL(req.url);

  // Skip non-GET requests
  if (req.method !== 'GET') return;

  // Skip Binance API and any external APIs — always go to network
  if (url.hostname !== self.location.hostname) return;

  // HTML navigation — NETWORK FIRST
  // Always fetch fresh HTML so updates are automatic
  if (req.mode === 'navigate' || url.pathname === '/') {
    e.respondWith(
      fetch(req, { cache: 'no-store' })
        .then(res => {
          if (res.ok) {
            // Cache the fresh copy for offline fallback
            const clone = res.clone();
            caches.open(CACHE_VER).then(c => c.put(req, clone));
          }
          return res;
        })
        .catch(() =>
          // Offline — serve cached version
          caches.match(req).then(cached => cached || caches.match('/'))
        )
    );
    return;
  }

  // Static assets (icons, manifest) — CACHE FIRST
  e.respondWith(
    caches.match(req).then(cached => {
      if (cached) return cached;
      return fetch(req).then(res => {
        if (res.ok) {
          const clone = res.clone();
          caches.open(CACHE_VER).then(c => c.put(req, clone));
        }
        return res;
      }).catch(() => new Response('', { status: 408 }));
    })
  );
});

// ── PUSH NOTIFICATIONS ────────────────────────────────────────
self.addEventListener('push', e => {
  const data = e.data ? e.data.json() : {};
  e.waitUntil(
    self.registration.showNotification(data.title || 'Quant Verse Signal', {
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
