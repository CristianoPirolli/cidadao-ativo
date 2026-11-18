from django.urls import path

from apps.core import pwa, views

urlpatterns = [
    path('', views.index, name='index'),
    path('health', views.healthcheck, name='healthcheck'),
    path('privacidade', views.privacy_policy, name='privacy_policy'),
    path('privacidade/aceitar', views.privacy_consent, name='privacy_consent'),
    path('manifest.webmanifest', pwa.manifest, name='manifest'),
    path('sw.js', pwa.service_worker, name='service_worker'),
    path('offline', pwa.offline, name='offline'),
]
