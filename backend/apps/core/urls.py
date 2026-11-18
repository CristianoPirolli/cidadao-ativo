from django.urls import path

from apps.core import pwa, views

urlpatterns = [
    path('', views.index, name='index'),
    path('health', views.healthcheck, name='healthcheck'),
    path('manifest.webmanifest', pwa.manifest, name='manifest'),
    path('sw.js', pwa.service_worker, name='service_worker'),
    path('offline', pwa.offline, name='offline'),
]
