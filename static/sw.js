const CACHE_NAME = 'mstodo-v2';
const PRECACHE_URLS = [
  '/',
  '/static/',
  '/static/favicon.svg',
  '/static/apple-touch-icon.png',
  '/static/ts.js',
  'https://cdn.tailwindcss.com',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css',
  'https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css',
  'https://cdn.jsdelivr.net/npm/sortablejs@1.15.0/Sortable.min.js'
];

// Install: precache shell
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        // Attempt to cache all URLs, but don't fail if some are unavailable
        return Promise.allSettled(
          PRECACHE_URLS.map(url => cache.add(url))
        );
      })
      .then(() => self.skipWaiting())
  );
});

// Activate: clean up old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((names) => {
      return Promise.all(
        names.map((name) => {
          if (name !== CACHE_NAME) {
            return caches.delete(name);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch: implement cache strategies
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Network-first for API requests
  if (url.pathname.startsWith('/api/')) {
    return event.respondWith(networkFirstStrategy(request, 3000));
  }

  // Stale-while-revalidate for CDN resources and external dependencies
  if (url.hostname.includes('cdn.') || 
      url.hostname.includes('jsdelivr.net') ||
      url.hostname.includes('cdnjs.com') ||
      url.hostname.includes('cloudflare.com')) {
    return event.respondWith(staleWhileRevalidateStrategy(request));
  }

  // Cache-first for app shell and static assets
  return event.respondWith(cacheFirstStrategy(request));
});

// Network-first: fetch from network, fallback to cache after timeout
async function networkFirstStrategy(request, timeout = 3000) {
  const fetchPromise = fetch(request);
  const timeoutPromise = new Promise((_, reject) =>
    setTimeout(() => reject(new Error('Network timeout')), timeout)
  );

  try {
    const response = await Promise.race([fetchPromise, timeoutPromise]);
    if (response.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, response.clone());
      return response;
    }
    return response;
  } catch (error) {
    const cached = await caches.match(request);
    return cached || new Response('Network error and no cache', { status: 503 });
  }
}

// Stale-while-revalidate: serve from cache, update in background
async function staleWhileRevalidateStrategy(request) {
  const cached = await caches.match(request);
  
  const fetchPromise = fetch(request).then((response) => {
    if (response.ok) {
      const cache = caches.open(CACHE_NAME);
      cache.then((c) => c.put(request, response.clone()));
    }
    return response;
  });

  return cached || fetchPromise;
}

// Cache-first: serve from cache, fallback to network
async function cacheFirstStrategy(request) {
  const cached = await caches.match(request);
  if (cached) {
    // Update cache in background
    fetch(request).then((response) => {
      if (response.ok) {
        const cache = caches.open(CACHE_NAME);
        cache.then((c) => c.put(request, response.clone()));
      }
    }).catch(() => {});
    
    return cached;
  }

  return fetch(request).then((response) => {
    if (response.ok) {
      const cache = caches.open(CACHE_NAME);
      cache.then((c) => c.put(request, response.clone()));
    }
    return response;
  });
}

// === Web Push 알림 (push-service) ===
self.addEventListener('push', event => {
  let d = {};
  try { d = event.data ? event.data.json() : {}; } catch (e) { d = { body: event.data && event.data.text() }; }
  event.waitUntil(self.registration.showNotification(d.title || '알림', {
    body: d.body || '',
    tag: d.tag || undefined,
    data: { url: d.url || '/' }
  }));
});

self.addEventListener('notificationclick', event => {
  event.notification.close();
  const url = new URL(event.notification.data?.url || '/', self.location.origin).href;
  event.waitUntil(clients.matchAll({ type: 'window', includeUncontrolled: true }).then(list => {
    for (const c of list) if (c.url === url && 'focus' in c) return c.focus();
    return clients.openWindow(url);
  }));
});
