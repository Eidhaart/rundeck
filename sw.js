/* RunDeck service worker: keeps the app working offline.
   Page and config: network first, so updates arrive as soon as you are online.
   Sounds and icons: cached and refreshed in the background.
   Requests to other sites (Supabase, the CDN, fonts, Turnstile) are never touched, so the browser loads them normally. */
const V='rundeck-v2';
const CORE=['/','/index.html','/config.js','/privacy.html','/manifest.webmanifest','/icons/icon-192.png','/icons/icon-512.png','/icons/favicon-64.png',
 '/sfx/complete_1.mp3','/sfx/complete_2.mp3','/sfx/complete_3.mp3','/sfx/complete_heavy.mp3','/sfx/hack_complete.mp3','/sfx/ping.mp3','/sfx/detected.mp3','/sfx/levelup.mp3','/sfx/heat.mp3','/sfx/ring.mp3','/sfx/jackin.mp3','/sfx/boot.mp3','/sfx/error.mp3'];
self.addEventListener('install',e=>{e.waitUntil(caches.open(V).then(c=>Promise.all(CORE.map(u=>c.add(u).catch(()=>{})))).then(()=>self.skipWaiting()))});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==V).map(k=>caches.delete(k)))).then(()=>self.clients.claim()))});
const NEVER=/supabase\.co|challenges\.cloudflare\.com/;
self.addEventListener('fetch',e=>{const r=e.request;if(r.method!=='GET')return;const u=new URL(r.url);
 const same=u.origin===self.location.origin;if(!same||NEVER.test(u.hostname))return;
 if(same&&(r.mode==='navigate'||u.pathname==='/'||u.pathname.endsWith('.html')||u.pathname==='/config.js')){
  e.respondWith(fetch(r).then(res=>{if(res.ok){const cp=res.clone();caches.open(V).then(c=>c.put(r.mode==='navigate'?'/index.html':r,cp))}return res}).catch(()=>caches.match(r.mode==='navigate'?'/index.html':r).then(m=>m||caches.match('/'))));return}
 if(same){
  e.respondWith(caches.open(V).then(c=>c.match(r).then(m=>{const net=fetch(r).then(res=>{if(res&&res.ok)c.put(r,res.clone());return res}).catch(()=>m);return m||net})))}});
