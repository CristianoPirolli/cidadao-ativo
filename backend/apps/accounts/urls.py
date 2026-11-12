from django.urls import path

from apps.accounts import views

urlpatterns = [
    path('login', views.login_view, name='login'),
    path('register', views.register_view, name='register'),
    path('logout', views.logout_view, name='logout'),

    # Administrador
    path('admin/users/<int:user_id>/edit', views.edit_user_by_admin, name='edit_user_by_admin'),
    path('admin/approve/<int:user_id>', views.approve_user, name='approve_user'),
    path('admin/reject/<int:user_id>', views.reject_user, name='reject_user'),
    path('admin/activate/<int:user_id>', views.activate_user, name='activate_user'),

    # Dono da plataforma
    path('owner/toggle-admin/<int:user_id>', views.toggle_admin, name='toggle_admin'),
    path('owner/reset-password/<int:user_id>', views.reset_user_password, name='reset_user_password'),

    # Órgão
    path('orgao/aprovar-cidadao/<int:user_id>', views.agency_approve_citizen, name='agency_approve_citizen'),
    path('orgao/rejeitar-cidadao/<int:user_id>', views.agency_reject_citizen, name='agency_reject_citizen'),
    path('orgao/comprovante/<int:user_id>', views.view_residence_proof, name='view_residence_proof'),
]
