// service-worker.js
// TipsyTheoryy PWA Service Worker
// Version: 1.0.1 - Update this version number when you make changes!

const CACHE_VERSION = 'v3.0.5'; // Increment this to force cache update
const CACHE_NAME = `tipsytheoryy-cache-${CACHE_VERSION}`;
const OFFLINE_URL = '/offline/'; // Django URL pattern

// Assets to cache immediately on install
const PRECACHE_ASSETS = [
  "/",
  "/static/styles.css",
  "/static/js/order_detail.js",
  "/static/js/homepage.js",
  "/static/images/favicon.png",
  "/static/images/bg.jpeg",
  "/static/images/bg-pattern.jpg",
  "/manifest.json",
  OFFLINE_URL,
];

// Assets to cache on first request (runtime caching)
const RUNTIME_CACHE_URLS = [
  /^\/static\//,
  /^\/media\//,
];

// Install event - cache critical assets
self.addEventListener('install', (event) => {
  console.log('[Service Worker] Installing version:', CACHE_VERSION);
  
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('[Service Worker] Precaching assets');
        return cache.addAll(PRECACHE_ASSETS)
          .catch((error) => {
            console.error('[Service Worker] Precache failed:', error);
            // Continue even if some assets fail
            return Promise.resolve();
          });
      })
      .then(() => {
        console.log('[Service Worker] Skip waiting');
        return self.skipWaiting(); // Activate immediately
      })
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  console.log('[Service Worker] Activating version:', CACHE_VERSION);
  
  event.waitUntil(
    caches.keys()
      .then((cacheNames) => {
        // Delete old caches
        return Promise.all(
          cacheNames.map((cacheName) => {
            if (cacheName !== CACHE_NAME) {
              console.log('[Service Worker] Deleting old cache:', cacheName);
              return caches.delete(cacheName);
            }
          })
        );
      })
      .then(() => {
        console.log('[Service Worker] Claiming clients');
        return self.clients.claim(); // Take control of all pages immediately
      })
  );
});

// Fetch event - serve from cache or network
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip caching for:
  // 1. Non-GET requests
  // 2. Chrome extensions
  // 3. Admin panel
  // 4. API endpoints (you might want to cache some API responses)
  if (
    request.method !== 'GET' ||
    url.protocol === 'chrome-extension:' ||
    url.pathname.startsWith('/backend/') ||
    url.pathname.startsWith('/api/')
  ) {
    return;
  }

  // Handle manifest.json specially - always fetch fresh
  if (url.pathname.endsWith('manifest.json')) {
    event.respondWith(
      fetch(request)
        .then((response) => {
          // Clone and cache the fresh manifest
          const responseClone = response.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(request, responseClone);
          });
          return response;
        })
        .catch(() => {
          // Return cached manifest as fallback
          return caches.match(request);
        })
    );
    return;
  }

  // Network-first strategy for HTML pages (to get latest content)
  if (request.headers.get('accept').includes('text/html')) {
    event.respondWith(
      fetch(request)
        .then((response) => {
          // Clone and cache successful response
          if (response && response.status === 200) {
            const responseClone = response.clone();
            caches.open(CACHE_NAME).then((cache) => {
              cache.put(request, responseClone);
            });
          }
          return response;
        })
        .catch(() => {
          // Network failed, try cache
          return caches.match(request)
            .then((cachedResponse) => {
              if (cachedResponse) {
                return cachedResponse;
              }
              // No cached version, return offline page
              return caches.match(OFFLINE_URL);
            });
        })
    );
    return;
  }

  // Cache-first strategy for static assets (CSS, JS, images)
  event.respondWith(
    caches.match(request)
      .then((cachedResponse) => {
        if (cachedResponse) {
          return cachedResponse;
        }

        // Not in cache, fetch from network
        return fetch(request)
          .then((response) => {
            // Check if this is a static asset worth caching
            const shouldCache = RUNTIME_CACHE_URLS.some(pattern => 
              pattern.test(url.pathname)
            );

            if (shouldCache && response && response.status === 200) {
              const responseClone = response.clone();
              caches.open(CACHE_NAME).then((cache) => {
                cache.put(request, responseClone);
              });
            }

            return response;
          })
          .catch((error) => {
            console.log('[Service Worker] Fetch failed:', error);
            // For images, return a placeholder if available
            if (request.destination === 'image') {
              return caches.match('/static/images/placeholder.png');
            }
          });
      })
  );
});

// Listen for messages from the client
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
  
  if (event.data && event.data.type === 'CACHE_URLS') {
    // Allow client to request caching of specific URLs
    const urls = event.data.urls;
    event.waitUntil(
      caches.open(CACHE_NAME)
        .then((cache) => cache.addAll(urls))
    );
  }
});

// Background sync for offline form submissions (optional)
self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-orders') {
    event.waitUntil(
      // Handle offline order sync here
      syncOfflineOrders()
    );
  }
});

async function syncOfflineOrders() {
  // Implementation for syncing offline orders
  console.log('[Service Worker] Syncing offline orders');
  // This would retrieve orders from IndexedDB and send them to server
}