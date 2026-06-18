const CACHE_NAME = 'borsa-sinyal-v1';

self.addEventListener('install', e => {
    self.skipWaiting();
});

self.addEventListener('fetch', e => {
    // Network-first stratejisi
    e.respondWith(
        fetch(e.request).catch(() => caches.match(e.request))
    );
});