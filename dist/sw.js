// Clear older versions that saved the public portal for offline viewing.
self.addEventListener('install', event => event.waitUntil(self.skipWaiting()));
self.addEventListener('activate', event => {
 event.waitUntil((async () => {
  for (const key of await caches.keys()) {
   if (key.startsWith('castelo-partner-')) await caches.delete(key);
  }
  await self.clients.claim();
 })());
});
