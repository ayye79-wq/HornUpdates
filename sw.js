const CACHE_VERSION = "ethio-pulse-v2";
const APP_SHELL_CACHE = `app-shell-${CACHE_VERSION}`;
const DATA_CACHE = `data-${CACHE_VERSION}`;

const APP_SHELL_FILES = [
  "/",
  "/index.html",
  "/style.css",
  "/manifest.json",
  "/icons/icon-192.png",
  "/icons/icon-512.png",
  "/Horn1_logo.png",
  "/favicon.ico"
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(APP_SHELL_CACHE).then((cache) => cache.addAll(APP_SHELL_FILES))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((k) => ![APP_SHELL_CACHE, DATA_CACHE].includes(k))
          .map((k) => caches.delete(k))
      )
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  const url = new URL(req.url);

  // Only handle same-origin
  if (url.origin !== location.origin) return;

  // 1) News data: network-first, fallback to cache
  if (url.pathname.endsWith("/articles.json")) {
    event.respondWith(networkFirst(req, DATA_CACHE));
    return;
  }

  // 1b) Manifest + icons: network-first (prevents stale install metadata/icons)
  if (
    url.pathname === "/manifest.json" ||
    url.pathname.startsWith("/icons/") ||
    url.pathname === "/favicon.ico"
  ) {
    event.respondWith(networkFirst(req, APP_SHELL_CACHE));
    return;
  }

  // 2) App shell / static: cache-first
  if (
    req.method === "GET" &&
    (APP_SHELL_FILES.includes(url.pathname) ||
      url.pathname.endsWith(".png") ||
      url.pathname.endsWith(".jpg") ||
      url.pathname.endsWith(".jpeg") ||
      url.pathname.endsWith(".webp") ||
      url.pathname.endsWith(".css") ||
      url.pathname.endsWith(".js"))
  ) {
    event.respondWith(cacheFirst(req, APP_SHELL_CACHE));
    return;
  }

  // Default: try network, fallback to cache
  event.respondWith(networkFallbackCache(req));
});

// --- Strategies ---
async function cacheFirst(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);
  if (cached) return cached;

  const fresh = await fetch(request);
  cache.put(request, fresh.clone());
  return fresh;
}

async function networkFirst(request, cacheName) {
  const cache = await caches.open(cacheName);
  try {
    const fresh = await fetch(request);
    cache.put(request, fresh.clone());
    return fresh;
  } catch (e) {
    const cached = await cache.match(request);
    if (cached) return cached;
    return new Response(JSON.stringify({ articles: [] }), {
      headers: { "Content-Type": "application/json" }
    });
  }
}

async function networkFallbackCache(request) {
  const cache = await caches.open(APP_SHELL_CACHE);
  try {
    const fresh = await fetch(request);
    cache.put(request, fresh.clone());
    return fresh;
  } catch (e) {
    const cached = await cache.match(request);
    return cached || Response.error();
  }
}
