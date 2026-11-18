"""
Recursos do app instalável (PWA): manifesto, service worker e página offline.

O service worker é servido pela raiz (``/sw.js``) para controlar todas as
páginas. Ele guarda apenas arquivos estáticos e a página offline: as páginas
do usuário nunca são armazenadas no aparelho, para não expor dados pessoais
em celulares compartilhados.
"""
import hashlib
import json
import os

from django.conf import settings
from django.contrib.staticfiles import finders
from django.http import JsonResponse
from django.shortcuts import render
from django.templatetags.static import static
from django.urls import reverse
from django.views.decorators.cache import cache_control, never_cache
from django.views.decorators.http import require_GET

APP_NAME = 'Cidadão Ativo'
THEME_COLOR = '#1f6feb'
BACKGROUND_COLOR = '#f2f5ff'

# Arquivos guardados no aparelho na instalação (carregamento rápido e offline)
PRECACHE_STATIC = [
    'css/styles.css',
    'js/app.js',
    'vendor/bootstrap/bootstrap.min.css',
    'vendor/bootstrap/bootstrap.bundle.min.js',
    'vendor/bootstrap-icons/bootstrap-icons.min.css',
    'vendor/bootstrap-icons/fonts/bootstrap-icons.woff2',
    'vendor/leaflet/leaflet.css',
    'vendor/leaflet/leaflet.js',
    'vendor/leaflet/images/marker-icon.png',
    'vendor/leaflet/images/marker-icon-2x.png',
    'vendor/leaflet/images/marker-shadow.png',
    'icons/icon-192.png',
    'icons/favicon-32.png',
]


def _cache_version(urls):
    """Muda sempre que um arquivo guardado muda, forçando a atualização do cache."""
    digest = hashlib.sha256('|'.join(urls).encode())
    if settings.DEBUG:
        # Em desenvolvimento os nomes não têm hash: usa a data de modificação
        for name in PRECACHE_STATIC:
            path = finders.find(name)
            if path:
                digest.update(str(os.path.getmtime(path)).encode())
    return digest.hexdigest()[:12]


@require_GET
@cache_control(max_age=86400, public=True)
def manifest(request):
    icons = [
        {'src': static('icons/icon-192.png'), 'sizes': '192x192', 'type': 'image/png'},
        {'src': static('icons/icon-512.png'), 'sizes': '512x512', 'type': 'image/png'},
        {'src': static('icons/icon-maskable-512.png'), 'sizes': '512x512', 'type': 'image/png', 'purpose': 'maskable'},
    ]
    data = {
        'id': '/',
        'name': APP_NAME,
        'short_name': APP_NAME,
        'description': 'Registre e acompanhe problemas urbanos da sua cidade.',
        'lang': 'pt-BR',
        'dir': 'ltr',
        'start_url': reverse('dashboard') + '?origem=app',
        'scope': '/',
        'display': 'standalone',
        'orientation': 'portrait',
        'theme_color': THEME_COLOR,
        'background_color': BACKGROUND_COLOR,
        'categories': ['government', 'utilities'],
        'icons': icons,
        'shortcuts': [
            {
                'name': 'Novo chamado',
                'short_name': 'Novo chamado',
                'url': reverse('denuncia'),
                'icons': [{'src': static('icons/icon-192.png'), 'sizes': '192x192'}],
            },
        ],
    }
    response = JsonResponse(data, json_dumps_params={'ensure_ascii': False})
    response['Content-Type'] = 'application/manifest+json'
    return response


@require_GET
@never_cache
def service_worker(request):
    precache = [static(name) for name in PRECACHE_STATIC]
    offline_url = reverse('offline')
    response = render(request, 'core/sw.js', {
        'version': _cache_version([*precache, offline_url]),
        'precache_json': json.dumps([*precache, offline_url]),
        'offline_url_json': json.dumps(offline_url),
        'static_prefix_json': json.dumps(settings.STATIC_URL),
    }, content_type='application/javascript')
    # Permite que o script controle todo o site, mesmo atrás de proxy
    response['Service-Worker-Allowed'] = '/'
    return response


@require_GET
def offline(request):
    return render(request, 'core/offline.html')
