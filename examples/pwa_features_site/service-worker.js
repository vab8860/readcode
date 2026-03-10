self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open('readcode-v1').then((cache) =>
      cache.addAll(['./', './index.html', './styles.css', './script.js', './manifest.json'])
    )
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener('fetch', (event) => {
  event.respondWith(
    caches.match(event.request).then((cached) => cached || fetch(event.request))
  );
});
