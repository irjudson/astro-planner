// Service Worker for caching preview images
const CACHE_NAME = 'astro-planner-images-v1';
const IMAGE_CACHE_DURATION = 30 * 24 * 60 * 60 * 1000; // 30 days in milliseconds

self.addEventListener('install', (event) => {
    console.log('Service Worker: Installing...');
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    console.log('Service Worker: Activating...');
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((cacheName) => {
                    if (cacheName !== CACHE_NAME) {
                        console.log('Service Worker: Deleting old cache', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
    return self.clients.claim();
});

self.addEventListener('fetch', (event) => {
    const url = new URL(event.request.url);

    // Only cache image requests to /api/images/targets/
    if (url.pathname.startsWith('/api/images/targets/')) {
        event.respondWith(
            caches.open(CACHE_NAME).then((cache) => {
                return cache.match(event.request).then((cachedResponse) => {
                    // Check if we have a cached response
                    if (cachedResponse) {
                        // Check cache age
                        const cachedDate = new Date(cachedResponse.headers.get('date'));
                        const age = Date.now() - cachedDate.getTime();

                        if (age < IMAGE_CACHE_DURATION) {
                            console.log('Service Worker: Serving from cache', url.pathname);
                            return cachedResponse;
                        }
                        console.log('Service Worker: Cache expired, fetching fresh', url.pathname);
                    }

                    // Fetch from network
                    return fetch(event.request)
                        .then((networkResponse) => {
                            // Only cache successful responses (200-299)
                            if (networkResponse.ok) {
                                console.log('Service Worker: Caching new image', url.pathname);
                                cache.put(event.request, networkResponse.clone());
                            } else {
                                // Cache 404s for a shorter time (1 hour) to retry failed fetches
                                if (networkResponse.status === 404) {
                                    console.log('Service Worker: Caching 404 temporarily', url.pathname);
                                    const responseToCache = networkResponse.clone();
                                    // Store with a header indicating short cache time
                                    cache.put(event.request, responseToCache);
                                }
                            }
                            return networkResponse;
                        })
                        .catch((error) => {
                            console.error('Service Worker: Fetch failed', url.pathname, error);
                            // Return cached response even if expired if network fails
                            if (cachedResponse) {
                                console.log('Service Worker: Network failed, using stale cache', url.pathname);
                                return cachedResponse;
                            }
                            throw error;
                        });
                });
            })
        );
    } else {
        // For non-image requests, just pass through
        event.respondWith(fetch(event.request));
    }
});
