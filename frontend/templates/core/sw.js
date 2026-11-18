/* Service worker do Cidadão Ativo — gerado por apps/core/pwa.py */
const CACHE = 'cidadao-ativo-{{ version }}';
const PRECACHE = {{ precache_json|safe }};
const OFFLINE_URL = {{ offline_url_json|safe }};
const STATIC_PREFIX = {{ static_prefix_json|safe }};

self.addEventListener('install', (event) => {
  // Sem cookies: a página offline guardada é sempre anônima (sem nome do usuário
  // nem mensagens da sessão, que seriam consumidas por esta requisição)
  const requests = PRECACHE.map((url) => new Request(url, { credentials: 'omit' }));
  event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(requests)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((key) => key !== CACHE).map((key) => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;
  const url = new URL(request.url);

  // Páginas: sempre da rede (dados pessoais não ficam no aparelho); sem conexão, página offline
  if (request.mode === 'navigate') {
    event.respondWith(fetch(request).catch(() => caches.match(OFFLINE_URL)));
    return;
  }

  // Arquivos estáticos: do aparelho primeiro, rede como reserva
  if (url.origin === self.location.origin && url.pathname.startsWith(STATIC_PREFIX)) {
    event.respondWith(
      caches.match(request).then((cached) => cached || fetch(request).then((response) => {
        if (response.ok) {
          const copy = response.clone();
          caches.open(CACHE).then((cache) => cache.put(request, copy));
        }
        return response;
      }))
    );
  }
});
