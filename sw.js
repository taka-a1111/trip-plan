/* 旅のしおり Service Worker
   - 同一オリジンのHTML等: ネット優先（更新が最優先）→ 圏外時はキャッシュ
   - 天気API(open-meteo/jma): ネット優先・キャッシュには保存しない（古い天気を出さない）
   - 地図タイル/CDN/フォント: キャッシュ優先＋裏で更新（圏外でも表示を保つ） */
var CACHE = 'trip-plan-v5';
var CORE = ['./', './index.html', './kiso.html', './hokuriku.html', './manifest.json'];

self.addEventListener('install', function (e) {
  e.waitUntil(caches.open(CACHE).then(function (c) {
    return Promise.all(CORE.map(function (u) { return c.add(u).catch(function () {}); }));
  }).then(function () { return self.skipWaiting(); }));
});

self.addEventListener('activate', function (e) {
  e.waitUntil(caches.keys().then(function (ks) {
    return Promise.all(ks.filter(function (k) { return k !== CACHE; }).map(function (k) { return caches.delete(k); }));
  }).then(function () { return self.clients.claim(); }));
});

self.addEventListener('fetch', function (e) {
  var req = e.request;
  if (req.method !== 'GET') return;
  var url = new URL(req.url);
  var isWeather = /open-meteo\.com|jma\.go\.jp/.test(url.host);
  var isSameOrigin = url.origin === self.location.origin;

  if (isWeather) {
    e.respondWith(fetch(req).catch(function () { return caches.match(req); }));
    return;
  }
  if (isSameOrigin || req.mode === 'navigate') {
    // ネット優先: 成功したらキャッシュ更新、失敗（圏外）ならキャッシュ
    e.respondWith(
      fetch(req).then(function (r) {
        if (r && r.ok) {
          var cp = r.clone();
          caches.open(CACHE).then(function (c) { c.put(req, cp); });
        }
        return r;
      }).catch(function () {
        return caches.match(req, { ignoreSearch: true }).then(function (m) {
          return m || caches.match('./index.html');
        });
      })
    );
    return;
  }
  // CDN・タイル・フォント: キャッシュ優先＋裏で更新
  e.respondWith(
    caches.match(req).then(function (m) {
      var f = fetch(req).then(function (r) {
        if (r && (r.ok || r.type === 'opaque')) {
          var cp = r.clone();
          caches.open(CACHE).then(function (c) { c.put(req, cp); });
        }
        return r;
      }).catch(function () { return m; });
      return m || f;
    })
  );
});
