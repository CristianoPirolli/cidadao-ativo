"""Rotas principais do projeto."""
from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

urlpatterns = [
    path('django-admin/', admin.site.urls),
    path('', include('apps.core.urls')),
    path('', include('apps.accounts.urls')),
    path('', include('apps.reports.urls')),
    path('', include('apps.ouvidoria.urls')),
    path('', include('apps.dashboards.urls')),
    path('api/', include('apps.reports.api_urls')),
    path('api/', include('apps.locations.urls')),
]

if settings.SERVE_MEDIA:
    # Comprovantes de residência ficam fora desta rota de propósito: só são
    # acessíveis pela view autenticada ``view_residence_proof``.
    urlpatterns += [
        re_path(
            rf'^{settings.MEDIA_URL.lstrip("/")}(?!residence_proofs/)(?P<path>.*)$',
            serve,
            {'document_root': settings.MEDIA_ROOT},
        ),
    ]

admin.site.site_header = 'Cidadão Ativo — Administração'
admin.site.site_title = 'Cidadão Ativo'
