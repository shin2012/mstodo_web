const CACHE_NAME = 'mstodo-v1';
const PRECACHE_URLS = [
  '/', '/static/ts.js', '/static/favicon.svg', '/static/apple-touch-icon.png',
  'https://cdn.tailwindcss.com',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css',
  'https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css',
  'https://cdn.jsdelivr.net/npm/sortablejs@1.15.0/Sortable.min.js'
];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE_NAME)
      .then(c => c.addAll(PRECACHE_URLS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);

  // API: network-first, 3s timeout, cache fallback
  if (url.pathname.startsWith('/api/')) {
    e.respondWith(
      Promise.race([
        fetch(e.request).then(r => {
          if (r.ok) {
            const clone = r.clone();
            caches.open(CACHE_NAME).then(c => c.put(e.request, clone));
          }
          return r;
        }),
        new Promise((_, reject) => setTimeout(reject, 3000))
      ]).catch(() => caches.match(e.request))
    );
    return;
  }

  // Everything else: cache-first, revalidate in background
  e.respondWith(
    caches.match(e.request).then(cached => {
      const fetched = fetch(e.request).then(r => {
        if (r.ok) {
          const clone = r.clone();
          caches.open(CACHE_NAME).then(c => c.put(e.request, clone));
        }
        return r;
      }).catch(() => cached);
      return cached || fetched;
    })
  );
});
