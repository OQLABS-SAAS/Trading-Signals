     1|// ─────────────────────────────────────────────────────────────
     2|//  DOTVERSE — Service Worker
     3|//  Strategy:
     4|//    • HTML  → network-first  (always loads latest deploy)
     5|//    • Icons → cache-first    (static, load instantly)
     6|//    • API   → bypass cache   (live Binance data, never cached)
     7|//
     8|//  To force a full cache wipe on next deploy: bump CACHE_VER
     9|// ─────────────────────────────────────────────────────────────
    10|const CACHE_VER = 'dv-v5';
    11|const STATIC_ASSETS = [
    12|  '/icon-192.png',
    13|  '/icon-512.png',
    14|  '/apple-touch-icon.png',
    15|];
    16|
    17|// ── INSTALL: cache static assets, activate immediately ───────
    18|self.addEventListener('install', e => {
    19|  self.skipWaiting(); // Don't wait — activate right away
    20|  e.waitUntil(
    21|    caches.open(CACHE_VER).then(c => c.addAll(STATIC_ASSETS).catch(()=>{}))
    22|  );
    23|});
    24|
    25|// ── ACTIVATE: delete old caches, claim all open pages ────────
    26|self.addEventListener('activate', e => {
    27|  e.waitUntil(
    28|    caches.keys()
    29|      .then(keys => Promise.all(
    30|        keys.filter(k => k !== CACHE_VER).map(k => {
    31|          console.log('[QV SW] Deleting old cache:', k);
    32|          return caches.delete(k);
    33|        })
    34|      ))
    35|      .then(() => self.clients.claim()) // Take control of all tabs immediately
    36|  );
    37|});
    38|
    39|// ── FETCH: smart routing by request type ─────────────────────
    40|self.addEventListener('fetch', e => {
    41|  const req = e.request;
    42|  const url = new URL(req.url);
    43|
    44|  // Skip non-GET requests
    45|  if (req.method !== 'GET') return;
    46|
    47|  // Skip Binance API and any external APIs — always go to network
    48|  if (url.hostname !== self.location.hostname) return;
    49|
    50|  // HTML navigation — NETWORK FIRST
    51|  // Always fetch fresh HTML so updates are automatic
    52|  if (req.mode === 'navigate' || url.pathname === '/') {
    53|    e.respondWith(
    54|      fetch(req, { cache: 'no-store' })
    55|        .then(res => {
    56|          if (res.ok) {
    57|            // Cache the fresh copy for offline fallback
    58|            const clone = res.clone();
    59|            caches.open(CACHE_VER).then(c => c.put(req, clone));
    60|          }
    61|          return res;
    62|        })
    63|        .catch(() =>
    64|          // Offline — serve cached version
    65|          caches.match(req).then(cached => cached || caches.match('/'))
    66|        )
    67|    );
    68|    return;
    69|  }
    70|
    71|  // Static assets (icons, manifest) — CACHE FIRST
    72|  e.respondWith(
    73|    caches.match(req).then(cached => {
    74|      if (cached) return cached;
    75|      return fetch(req).then(res => {
    76|        if (res.ok) {
    77|          const clone = res.clone();
    78|          caches.open(CACHE_VER).then(c => c.put(req, clone));
    79|        }
    80|        return res;
    81|      }).catch(() => new Response('', { status: 408 }));
    82|    })
    83|  );
    84|});
    85|
    86|// ── PUSH NOTIFICATIONS ────────────────────────────────────────
    87|self.addEventListener('push', e => {
    88|  const data = e.data ? e.data.json() : {};
    89|  e.waitUntil(
    90|    self.registration.showNotification(data.title || 'Quant Verse Signal', {
    91|      body:    data.body  || 'New trading signal fired.',
    92|      icon:    '/icon-192.png',
    93|      badge:   '/icon-192.png',
    94|      tag:     data.tag   || 'signal',
    95|      data:    data.url   || '/',
    96|      vibrate: [200, 100, 200],
    97|    })
    98|  );
    99|});
   100|
   101|self.addEventListener('notificationclick', e => {
   102|  e.notification.close();
   103|  e.waitUntil(clients.openWindow(e.notification.data || '/'));
   104|});
   105|