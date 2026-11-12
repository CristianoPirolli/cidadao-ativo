"""Rotas da API de chamados (montadas em /api/)."""
from django.urls import path

from apps.reports import api

urlpatterns = [
    path('reports', api.get_reports, name='api_get_reports'),
    path('reports/create', api.create_report, name='api_create_report'),
    path('reports/<int:report_id>', api.get_report, name='api_get_report'),
    path('reports/<int:report_id>/update', api.update_report_status, name='api_update_report'),
    path('reports/<int:report_id>/delete', api.delete_report, name='api_delete_report'),
    path('reports/<int:report_id>/history', api.get_report_history, name='api_report_history'),
    path('reports/<int:report_id>/comment', api.add_comment, name='api_add_comment'),
    path('reports/<int:report_id>/vote', api.vote_report_urgency, name='api_vote_urgency'),
    path('stats', api.get_stats, name='api_stats'),
]
