from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.views.static import serve as serve_static

urlpatterns = [
    path('django-admin/', admin.site.urls),
    path('', include('core.urls')),
]

# django.conf.urls.static.static() só registra a rota quando DEBUG=True (checa
# de novo internamente, mesmo fora desse if). Não há proxy reverso separado
# servindo /uploads/ neste deploy (gunicorn serve tudo direto, como já é feito
# para estáticos via whitenoise), então registra a view direto, sem o helper.
urlpatterns += [
    re_path(
        r'^%s(?P<path>.*)$' % settings.MEDIA_URL.lstrip('/'),
        serve_static,
        {'document_root': settings.MEDIA_ROOT},
    ),
]
