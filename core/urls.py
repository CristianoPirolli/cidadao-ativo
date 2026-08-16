from django.urls import path
from core import views, api_views

urlpatterns = [
    # ── Páginas ──────────────────────────────────────────────────────────────
    path('', views.index, name='index'),
    path('login', views.login_view, name='login'),
    path('register', views.register_view, name='register'),
    path('logout', views.logout_view, name='logout'),
    path('denuncia', views.denuncia, name='denuncia'),
    path('qr-demo', views.qr_demo, name='qr_demo'),

    # Dashboards
    path('dashboard', views.dashboard, name='dashboard'),
    path('dashboard/cidadao', views.dashboard_citizen, name='dashboard_citizen'),
    path('dashboard/orgao', views.dashboard_agency, name='dashboard_agency'),
    path('dashboard/admin', views.dashboard_admin, name='dashboard_admin'),
    path('dashboard/owner', views.dashboard_owner, name='dashboard_owner'),

    # Relatório
    path('report/<int:report_id>', views.report_detail, name='report_detail'),

    # Ações de admin
    path('admin/users/<int:user_id>/edit', views.edit_user_by_admin, name='edit_user_by_admin'),
    path('admin/approve/<int:user_id>', views.approve_user, name='approve_user'),
    path('admin/reject/<int:user_id>', views.reject_user, name='reject_user'),
    path('admin/activate/<int:user_id>', views.activate_user, name='activate_user'),
    path('owner/toggle-admin/<int:user_id>', views.toggle_admin, name='toggle_admin'),
    path('owner/reset-password/<int:user_id>', views.reset_user_password, name='reset_user_password'),

    # Ações de órgão
    path('orgao/aprovar-cidadao/<int:user_id>', views.agency_approve_citizen, name='agency_approve_citizen'),
    path('orgao/rejeitar-cidadao/<int:user_id>', views.agency_reject_citizen, name='agency_reject_citizen'),
    path('orgao/comprovante/<int:user_id>', views.view_residence_proof, name='view_residence_proof'),

    # Ouvidoria
    path('ouvidoria', views.ouvidoria, name='ouvidoria'),
    path('ouvidoria/<int:message_id>/inativar', views.inativar_mensagem_ouvidoria, name='inativar_mensagem_ouvidoria'),
    path('ouvidoria/<int:message_id>/reativar', views.reativar_mensagem_ouvidoria, name='reativar_mensagem_ouvidoria'),

    # ── API ──────────────────────────────────────────────────────────────────
    path('api/reports', api_views.get_reports, name='api_get_reports'),
    path('api/reports/create', api_views.create_report, name='api_create_report'),
    path('api/reports/<int:report_id>', api_views.get_report, name='api_get_report'),
    path('api/reports/<int:report_id>/update', api_views.update_report_status, name='api_update_report'),
    path('api/reports/<int:report_id>/delete', api_views.delete_report, name='api_delete_report'),
    path('api/reports/<int:report_id>/history', api_views.get_report_history, name='api_report_history'),
    path('api/reports/<int:report_id>/comment', api_views.add_comment, name='api_add_comment'),
    path('api/reports/<int:report_id>/vote', api_views.vote_report_urgency, name='api_vote_urgency'),
    path('api/stats', api_views.get_stats, name='api_stats'),
    path('api/municipios', api_views.get_municipios, name='api_municipios'),
    path('api/municipios/com-orgaos', api_views.get_municipios_com_orgaos, name='api_municipios_com_orgaos'),
    path('api/geocode', api_views.geocode, name='api_geocode'),
]
