/* Phoenix service worker: closed-tab alerts and an offline text page. */

const CACHE = "phoenix-v1";
const OFFLINE_URL = "/lite";

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE)
      .then((cache) => cache.add(new Request(OFFLINE_URL, { cache: "reload" })))
      .catch(() => undefined),
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)),
        ),
      )
      .then(() => self.clients.claim()),
  );
});

// Pages: network first. /lite is refreshed in the cache on every visit;
// when offline, any page falls back to the last copy of /lite.
self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET" || req.mode !== "navigate") return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;
  event.respondWith(
    fetch(req)
      .then((res) => {
        if (url.pathname === OFFLINE_URL && res.ok) {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(OFFLINE_URL, copy));
        }
        return res;
      })
      .catch(() =>
        caches.match(OFFLINE_URL).then((hit) => hit || Response.error()),
      ),
  );
});

self.addEventListener("push", (event) => {
  let data = {};
  try {
    data = event.data ? event.data.json() : {};
  } catch {
    data = { title: "Phoenix", body: event.data ? event.data.text() : "" };
  }
  // Only same-site links are opened from a notification
  const target =
    typeof data.url === "string" && data.url.startsWith("/") ? data.url : "/";
  event.waitUntil(
    self.registration.showNotification(data.title || "Phoenix", {
      body: data.body || "",
      tag: data.tag,
      icon: "/icon.svg",
      badge: "/icon.svg",
      data: { url: target },
    }),
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const target =
    (event.notification.data && event.notification.data.url) || "/";
  event.waitUntil(
    self.clients
      .matchAll({ type: "window", includeUncontrolled: true })
      .then((wins) => {
        for (const w of wins) {
          if ("focus" in w) {
            w.navigate(target);
            return w.focus();
          }
        }
        return self.clients.openWindow(target);
      }),
  );
});
