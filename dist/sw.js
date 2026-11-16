const CACHE='castelo-partner-v2';
const CORE=['./','./index.html','./styles.css','./app.js','./guide.js','./assets/guia/pagina-01.jpg','./data.js','./manifest.webmanifest','./assets/icon-192.png','./assets/icon-512.png','./assets/12Fw7rfB6u47WnVpw5K6mamMKQyNY7wfW.svg','./assets/1aiUPLwiyj7JUAOPa75_Ss3-GwQ7Ib0LN.webp'];
self.addEventListener('install',event=>{event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(CORE)).then(()=>self.skipWaiting()))});
self.addEventListener('activate',event=>{event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(key=>key.startsWith('castelo-partner-')&&key!==CACHE).map(key=>caches.delete(key)))).then(()=>self.clients.claim()))});
self.addEventListener('fetch',event=>{
 const req=event.request;if(req.method!=='GET'||new URL(req.url).origin!==self.location.origin)return;
 event.respondWith(fetch(req).then(response=>{if(response.ok){const copy=response.clone();event.waitUntil(caches.open(CACHE).then(cache=>cache.put(req,copy)))}return response}).catch(async()=>{const cached=await caches.match(req);if(cached)return cached;if(req.mode==='navigate')return caches.match('./index.html');return new Response('',{status:503,statusText:'Offline'})}));
});
