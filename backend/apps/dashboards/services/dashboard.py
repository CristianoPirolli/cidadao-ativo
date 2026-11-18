"""
Serviço de agregação de dados para os dashboards da aplicação.

As listas são devolvidas como querysets (ainda não executados) para que as
views as paginem; contagens e médias são calculadas pelo banco.
"""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

from django.db.models import Avg, Count, F, Q

from apps.accounts.models import User
from apps.reports.models import Report, ReportUrgencyVote

# Limite de marcadores no mapa do órgão (os mais urgentes primeiro)
MAP_REPORTS_LIMIT = 500


class DashboardError(Exception):
    """Erro genérico para problemas ao montar dashboards."""


STATUS_KEYS = ['aberto', 'visualizado', 'em_andamento', 'resolvido', 'rejeitado']


def _status_summary(queryset) -> dict[str, int]:
    counts = {key: 0 for key in STATUS_KEYS}
    total = 0
    for row in queryset.values('status').annotate(count=Count('id')).order_by():
        counts[row['status']] = row['count']
        total += row['count']
    counts['total'] = total
    return counts


def _resolution_metrics(queryset) -> dict[str, float | int | None]:
    resolved = queryset.filter(completed_at__isnull=False)
    data = resolved.aggregate(average=Avg(F('completed_at') - F('created_at')), count=Count('id'))
    average = data['average']
    return {
        'average_seconds': average.total_seconds() if average is not None else None,
        'resolved_count': data['count'],
    }


def _build_heatmap_points(coordinates: Iterable[tuple[float, float]], precision: int = 3) -> list[dict[str, object]]:
    """Agrupa coordenadas próximas (``precision`` casas decimais ≈ 100 m)."""
    clusters = defaultdict(lambda: {'sum_lat': 0.0, 'sum_lng': 0.0, 'count': 0})
    for lat, lng in coordinates:
        if lat is None or lng is None:
            continue
        cluster = clusters[(round(lat, precision), round(lng, precision))]
        cluster['sum_lat'] += lat
        cluster['sum_lng'] += lng
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


def order_reports_by_priority(queryset):
    """Ordena por votos de urgência (desc) e data de criação (desc), anotando ``vote_count``."""
    return queryset.annotate(vote_count=Count('urgency_votes', distinct=True)).order_by('-vote_count', '-created_at', '-id')


def voted_report_ids(user: User, reports: Iterable[Report]) -> set[int]:
    """IDs, entre ``reports``, dos chamados em que o cidadão já votou."""
    ids = [r.id for r in reports]
    if not ids:
        return set()
    return set(ReportUrgencyVote.objects.filter(user=user, report_id__in=ids).values_list('report_id', flat=True))


def get_citizen_dashboard_data(user: User) -> dict[str, object]:
    if not user.is_citizen:
        raise DashboardError('Acesso negado para dashboard de cidadão.')

    municipio_id = user.municipio_origem_id
    if not municipio_id:
        raise DashboardError('Cidadão sem município de origem configurado.')

    base_qs = Report.objects.filter(municipio_ibge_id=municipio_id)
    return {
        'reports': order_reports_by_priority(base_qs),
        'stats': _status_summary(base_qs),
    }


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

    reports = order_reports_by_priority(filtered_qs.select_related('user'))
    heat_points = _build_heatmap_points(base_qs.values_list('lat', 'lng'))

    return {
        'reports': reports,
        'map_reports': reports[:MAP_REPORTS_LIMIT],
        'stats': stats,
        'pending_citizens': pending_citizens,
        'filters': {'status': status_filter, 'category': category_filter},
        'resolution_metrics': _resolution_metrics(base_qs),
        'heat_points': heat_points,
        'hot_regions': heat_points[:5],
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

    stats = User.objects.aggregate(
        total=Count('id'),
        pending=Count('id', filter=Q(is_approved=False, is_admin=False)),
        approved=Count('id', filter=Q(is_approved=True)),
        citizens=Count('id', filter=Q(user_type='cidadao')),
        agencies=Count('id', filter=Q(user_type='orgao')),
    )
    report_stats = Report.objects.aggregate(
        total=Count('id'),
        aberto=Count('id', filter=Q(status='aberto')),
        em_andamento=Count('id', filter=Q(status='em_andamento')),
        resolvidos=Count('id', filter=Q(status='resolvido')),
        rejeitados=Count('id', filter=Q(status='rejeitado')),
    )

    return {
        'users': qs.order_by('-created_at', '-id'),
        'stats': stats,
        'report_stats': report_stats,
        'recent_reports': list(order_reports_by_priority(Report.objects.all())[:10]),
        'filter_type': filter_type,
    }
