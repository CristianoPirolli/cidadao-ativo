from django.urls import path

from apps.ouvidoria import views

urlpatterns = [
    path('ouvidoria', views.ouvidoria, name='ouvidoria'),
    path('ouvidoria/<int:message_id>/inativar', views.inativar_mensagem_ouvidoria, name='inativar_mensagem_ouvidoria'),
    path('ouvidoria/<int:message_id>/reativar', views.reativar_mensagem_ouvidoria, name='reativar_mensagem_ouvidoria'),
]
