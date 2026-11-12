from django.urls import path

from apps.dashboards import views

urlpatterns = [
    path('dashboard', views.dashboard, name='dashboard'),
    path('dashboard/cidadao', views.dashboard_citizen, name='dashboard_citizen'),
    path('dashboard/orgao', views.dashboard_agency, name='dashboard_agency'),
    path('dashboard/admin', views.dashboard_admin, name='dashboard_admin'),
    path('dashboard/owner', views.dashboard_owner, name='dashboard_owner'),
]
