"""
Serviço de agregação de dados para os dashboards da aplicação.
"""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

from django.db.models import Count, Q

from apps.accounts.models import User
from apps.reports.models import Report, ReportUrgencyVote


class DashboardError(Exception):
    """Erro genérico para problemas ao montar dashboards."""


STATUS_KEYS = ['aberto', 'visualizado', 'em_andamento', 'resolvido', 'rejeitado']


def _status_summary(queryset) -> dict[str, int]:
    counts = {key: 0 for key in STATUS_KEYS}
    rows = queryset.values('status').annotate(count=Count('id'))
    total = 0
    for row in rows:
        counts[row['status']] = row['count']
        total += row['count']
    counts['total'] = total
    return counts


def _compute_resolution_metrics(reports: Iterable[Report]) -> dict[str, float | None]:
    resolved = [r for r in reports if r.completed_at and r.created_at]
    if not resolved:
        return {'average_seconds': None, 'resolved_count': 0}
    total_seconds = sum((r.completed_at - r.created_at).total_seconds() for r in resolved)
    return {'average_seconds': total_seconds / len(resolved), 'resolved_count': len(resolved)}


def _build_heatmap_points(reports: Iterable[Report], precision: int = 3) -> list[dict[str, object]]:
    clusters = defaultdict(lambda: {'sum_lat': 0.0, 'sum_lng': 0.0, 'count': 0})
    for report in reports:
        if report.lat is None or report.lng is None:
            continue
        key = (round(report.lat, precision), round(report.lng, precision))
        cluster = clusters[key]
        cluster['sum_lat'] += report.lat
        cluster['sum_lng'] += report.lng
        cluster['count'] += 1
    points = [
        {
            'lat': v['sum_lat'] / v['count'],
            'lng': v['sum_lng'] / v['count'],
            'count': v['count'],
            'label': f'{k[0]:.3f}, {k[1]:.3f}',
        }
        for k, v in clusters.items()
    ]
    points.sort(key=lambda item: item['count'], reverse=True)
    return points


def _order_reports_by_priority(queryset):
    """Ordena por votos de urgência (desc) e data de criação (desc)."""
    return queryset.annotate(vote_count=Count('urgency_votes', distinct=True)).order_by('-vote_count', '-created_at')


def get_citizen_dashboard_data(user: User) -> dict[str, object]:
    if not user.is_citizen:
        raise DashboardError('Acesso negado para dashboard de cidadão.')

    municipio_id = user.municipio_origem_id
    if not municipio_id:
        raise DashboardError('Cidadão sem município de origem configurado.')

    base_qs = Report.objects.filter(municipio_ibge_id=municipio_id).select_related('user', 'assigned_user')
    reports = list(_order_reports_by_priority(base_qs))
    stats = _status_summary(Report.objects.filter(municipio_ibge_id=municipio_id))

    report_ids = [r.id for r in reports]
    voted_report_ids = set()
    if report_ids:
        voted_report_ids = set(
            ReportUrgencyVote.objects.filter(user=user, report_id__in=report_ids).values_list('report_id', flat=True)
        )

    return {'reports': reports, 'stats': stats, 'voted_report_ids': voted_report_ids}


def get_agency_dashboard_data(
    user: User,
    status_filter: str | None = None,
    category_filter: str | None = None,
) -> dict[str, object]:
    if not user.is_agency:
        raise DashboardError('Apenas órgãos podem acessar este dashboard.')

    municipio_id = user.municipio_ibge_id
    if not municipio_id:
        raise DashboardError('Órgão sem município configurado.')

    pending_citizens = list(
        User.objects.filter(
            user_type='cidadao', is_approved=False, is_active=True, municipio_origem_id=municipio_id
        ).order_by('-created_at')
    )

    base_qs = Report.objects.filter(municipio_ibge_id=municipio_id)
    stats = _status_summary(base_qs)
    stats['cidadaos_pendentes'] = len(pending_citizens)

    filtered_qs = base_qs
    if status_filter:
        filtered_qs = filtered_qs.filter(status=status_filter)
    if category_filter:
        filtered_qs = filtered_qs.filter(category=category_filter)

    reports = list(_order_reports_by_priority(filtered_qs.select_related('user', 'assigned_user')))

    municipality_reports = list(
        base_qs.select_related('user').order_by('created_at')
    )

    resolution_metrics = _compute_resolution_metrics(municipality_reports)
    heat_points = _build_heatmap_points(municipality_reports)
    hot_regions = heat_points[:5]

    return {
        'reports': reports,
        'stats': stats,
        'pending_citizens': pending_citizens,
        'filters': {'status': status_filter, 'category': category_filter},
        'resolution_metrics': resolution_metrics,
        'heat_points': heat_points,
        'hot_regions': hot_regions,
    }


def get_admin_dashboard_data(admin: User, filter_type: str = 'pending') -> dict[str, object]:
    if not admin.is_admin:
        raise DashboardError('Apenas administradores podem acessar este dashboard.')

    filter_type = filter_type or 'pending'

    qs = User.objects.all()
    if filter_type == 'pending':
        qs = qs.filter(is_approved=False, is_admin=False)
    elif filter_type == 'approved':
        qs = qs.filter(is_approved=True)

    users = list(qs.order_by('-created_at'))

    stats = User.objects.aggregate(
        total=Count('id'),
        pending=Count('id', filter=Q(is_approved=False, is_admin=False)),
        approved=Count('id', filter=Q(is_approved=True)),
        citizens=Count('id', filter=Q(user_type='cidadao')),
        agencies=Count('id', filter=Q(user_type='orgao')),
    )
    for key in stats:
        stats[key] = stats[key] or 0

    report_stats = {
        'total': Report.objects.count(),
        'aberto': Report.objects.filter(status='aberto').count(),
        'em_andamento': Report.objects.filter(status__in=['em_andamento', 'em_execucao']).count(),
        'resolvidos': Report.objects.filter(status__in=['resolvido', 'concluido']).count(),
        'rejeitados': Report.objects.filter(status='rejeitado').count(),
    }

    recent_reports = list(_order_reports_by_priority(Report.objects.select_related('user'))[:10])

    return {
        'users': users,
        'stats': stats,
        'report_stats': report_stats,
        'recent_reports': recent_reports,
        'filter_type': filter_type,
    }
