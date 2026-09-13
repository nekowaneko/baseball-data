//快取名稱含版本：cache-first 會一直吃舊檔，改了任何網站檔案或重新打包 payload 都要把這裡加一
const VERSION = 'v2'
const CACHE_NAME = `pitch-window-${VERSION}`
//只快取自己網域的五個檔；Pyodide 的 CDN 資源跨網域又大，交給瀏覽器自己的 HTTP 快取
const ASSETS = ['index.html', 'style.css', 'app.js', 'manifest.webmanifest', 'payload/pipeline.zip',
  'icon.svg', 'icons/icon-32.png', 'icons/icon-180.png', 'icons/icon-192.png',
  'icons/icon-512.png', 'icons/apple-touch-icon.png']

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS)))
})

//啟用時清掉舊版本的快取，避免手機裡同時堆好幾份 payload
self.addEventListener('activate', (event) => {
  event.waitUntil(caches.keys()
    .then((keys) => Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))))
    .then(() => self.clients.claim()))
})

//從主畫面開啟時請求的是目錄網址（./），要對應回快取裡的 index.html，飛航模式才開得起來
const cacheKeyFor = (request) => request.mode === 'navigate' ? 'index.html' : request

self.addEventListener('fetch', (event) => {
  const request = event.request
  if (request.method !== 'GET' || new URL(request.url).origin !== self.location.origin) return
  event.respondWith(caches.open(CACHE_NAME)
    .then((cache) => cache.match(cacheKeyFor(request), { ignoreSearch: true }))
    .then((hit) => hit || fetch(request)))
})
