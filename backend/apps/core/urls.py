from django.urls import path

from apps.core import views

urlpatterns = [
    path('', views.index, name='index'),
    path('qr-demo', views.qr_demo, name='qr_demo'),
    path('health', views.healthcheck, name='healthcheck'),
]
