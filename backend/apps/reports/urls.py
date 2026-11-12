from django.urls import path

from apps.reports import views

urlpatterns = [
    path('denuncia', views.denuncia, name='denuncia'),
    path('report/<int:report_id>', views.report_detail, name='report_detail'),
]
