"""Painéis por perfil: cidadão, órgão, administrador e dono da plataforma."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse

from apps.accounts.models import User, UserType
from apps.core.decorators import admin_required, agency_required, citizen_required, owner_required
from apps.dashboards.services.dashboard import (
    DashboardError,
    get_admin_dashboard_data,
    get_agency_dashboard_data,
    get_citizen_dashboard_data,
)
from apps.reports.models import Report, ReportStatus


def _dashboard_error(request, exc):
    # Renderiza a página em vez de redirecionar, para evitar loop entre
    # ``index`` → ``dashboard`` quando o cadastro está incompleto.
    return render(request, 'dashboards/error.html', {'error': str(exc)}, status=409)


@login_required
def dashboard(request):
    user = request.user
    if user.is_admin:
        return redirect('dashboard_admin')
    if user.is_citizen:
        return redirect('dashboard_citizen')
    if user.is_agency:
        return redirect('dashboard_agency')
    messages.error(request, 'Tipo de usuário não reconhecido')
    return redirect('index')


@citizen_required
def dashboard_citizen(request):
    try:
        data = get_citizen_dashboard_data(request.user)
    except DashboardError as exc:
        return _dashboard_error(request, exc)
    return render(request, 'dashboards/citizen.html', {
        'reports': data['reports'],
        'stats': data['stats'],
        'voted_report_ids': data.get('voted_report_ids', set()),
    })


def _build_map_context(reports, padding=0.02):
    """Monta os marcadores, limites e centro do mapa do painel do órgão."""
    map_reports = [
        {
            'id': report.id,
            'title': report.title,
            'category': report.category,
            'status': report.status_display,
            'status_raw': report.status,
            'lat': report.lat,
            'lng': report.lng,
            'created_at': report.created_at.strftime('%d/%m/%Y %H:%M') if report.created_at else '-',
            'detail_url': reverse('report_detail', args=[report.id]),
        }
        for report in reports
        if report.lat is not None and report.lng is not None
    ]
    if not map_reports:
        return map_reports, None, None

    latitudes = [item['lat'] for item in map_reports]
    longitudes = [item['lng'] for item in map_reports]

    def clamp(value, low, high):
        return max(low, min(value, high))

    bounds = {
        'southWest': {
            'lat': clamp(min(latitudes) - padding, -90, 90),
            'lng': clamp(min(longitudes) - padding, -180, 180),
        },
        'northEast': {
            'lat': clamp(max(latitudes) + padding, -90, 90),
            'lng': clamp(max(longitudes) + padding, -180, 180),
        },
    }
    center = {
        'lat': sum(latitudes) / len(latitudes),
        'lng': sum(longitudes) / len(longitudes),
    }
    return map_reports, bounds, center


@agency_required
def dashboard_agency(request):
    try:
        data = get_agency_dashboard_data(
            request.user,
            status_filter=request.GET.get('status') or None,
            category_filter=request.GET.get('category') or None,
        )
    except DashboardError as exc:
        return _dashboard_error(request, exc)

    map_reports, map_bounds, map_center = _build_map_context(data['reports'])

    return render(request, 'dashboards/agency.html', {
        'reports': data['reports'],
        'stats': data['stats'],
        'pending_citizens': data['pending_citizens'],
        'filters': data['filters'],
        'map_reports': map_reports,
        'map_bounds': map_bounds,
        'map_center': map_center,
        'resolution_metrics': data.get('resolution_metrics', {}),
        'heat_points': data.get('heat_points', []),
        'hot_regions': data.get('hot_regions', []),
    })


@admin_required
def dashboard_admin(request):
    try:
        data = get_admin_dashboard_data(request.user, filter_type=request.GET.get('filter', 'pending'))
    except DashboardError as exc:
        return _dashboard_error(request, exc)

    return render(request, 'dashboards/admin.html', {
        'users': data['users'],
        'stats': data['stats'],
        'report_stats': data['report_stats'],
        'recent_reports': data['recent_reports'],
        'filter_type': data['filter_type'],
    })


@owner_required
def dashboard_owner(request):
    agencies = User.objects.filter(user_type=UserType.AGENCY)
    pending_agencies = agencies.filter(is_approved=False, is_active=True)

    platform_stats = {
        'total_users': User.objects.count(),
        'total_agencies': agencies.count(),
        'pending_agencies': pending_agencies.count(),
        'total_citizens': User.objects.filter(user_type=UserType.CITIZEN).count(),
        'total_admins': User.objects.filter(is_admin=True).count(),
        'total_reports': Report.objects.count(),
        'open_reports': Report.objects.filter(status=ReportStatus.OPEN).count(),
        'resolved_reports': Report.objects.filter(status=ReportStatus.RESOLVED).count(),
        'municipalities': Report.objects.values('municipio_ibge_id').distinct().count(),
    }

    return render(request, 'dashboards/owner.html', {
        'tab': request.GET.get('tab', 'agencies'),
        'pending_agencies': pending_agencies.order_by('created_at'),
        'all_admins': User.objects.filter(is_admin=True).order_by('name'),
        'all_agencies': agencies.order_by('-created_at'),
        'platform_stats': platform_stats,
    })
