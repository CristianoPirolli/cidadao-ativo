"""Rotas da API de localidades (montadas em /api/)."""
from django.urls import path

from apps.locations import api

urlpatterns = [
    path('municipios', api.get_municipios, name='api_municipios'),
    path('municipios/com-orgaos', api.get_municipios_com_orgaos, name='api_municipios_com_orgaos'),
    path('geocode', api.geocode, name='api_geocode'),
]
