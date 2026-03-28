// Amygdala Service Worker — enables offline + push notifications
const CACHE_NAME = 'amygdala-v1';
const OFFLINE_URLS = ['/', '/static/manifest.json'];

// Install: cache the app shell
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(OFFLINE_URLS))
  );
  self.skipWaiting();
});

// Activate: clean old caches
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// Fetch: network-first for API, cache-first for app shell
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);

  // API calls: network-first, cache response for offline
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      fetch(event.request)
        .then(response => {
          // Cache successful API responses for offline use
          if (response.ok && event.request.method === 'GET') {
            const clone = response.clone();
            caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
          }
          return response;
        })
        .catch(() => {
          // Offline: try cache
          return caches.match(event.request).then(cached => {
            if (cached) return cached;
            // Return offline JSON for decision engine
            return new Response(JSON.stringify({
              instruction: "OFFLINE — Use downloaded offline pack. Call local emergency services.",
              action: "MONITOR",
              urgency: "MEDIUM",
              phase: "EVALUATE",
              confidence: 0,
              fallback_instruction: "Contact your embassy or nearest police station.",
              fallback_action: "STAY",
              threat_summary: "No data — device is offline",
              local_emergency_number: "112",
              trust_score: 0,
              sources_agreeing: 0,
              sources_total: 0
            }), { headers: { 'Content-Type': 'application/json' } });
          });
        })
    );
    return;
  }

  // App shell: cache-first
  event.respondWith(
    caches.match(event.request).then(cached => cached || fetch(event.request))
  );
});

// Push notifications
self.addEventListener('push', event => {
  const data = event.data ? event.data.json() : {};
  const title = data.title || 'Amygdala Alert';
  const options = {
    body: data.body || 'New threat detected in your area.',
    icon: '/static/icon-192.png',
    badge: '/static/icon-192.png',
    vibrate: [200, 100, 200, 100, 400],
    tag: 'amygdala-alert',
    renotify: true,
    requireInteraction: true,
    data: { url: data.url || '/' },
    actions: [
      { action: 'open', title: 'Open App' },
      { action: 'dismiss', title: 'Dismiss' }
    ]
  };
  event.waitUntil(self.registration.showNotification(title, options));
});

// Notification click
self.addEventListener('notificationclick', event => {
  event.notification.close();
  if (event.action === 'dismiss') return;
  event.waitUntil(
    clients.matchAll({ type: 'window' }).then(windowClients => {
      for (const client of windowClients) {
        if (client.url === '/' && 'focus' in client) return client.focus();
      }
      if (clients.openWindow) return clients.openWindow('/');
    })
  );
});
