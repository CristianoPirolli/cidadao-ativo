"""
Serviço de agregação de dados para os dashboards da aplicação.
Concentra consultas e cálculos de estatísticas em um único lugar.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional
from collections import defaultdict

from sqlalchemy import case, func

from app.models.models import Report, User, db


class DashboardError(Exception):
    """Erro genérico para problemas ao montar dashboards."""


STATUS_KEYS = ["aberto", "visualizado", "em_andamento", "concluido", "avaliado", "rejeitado"]


def _status_summary(query) -> Dict[str, int]:
    """
    Retorna um dicionário com contagem de chamados por status para a query informada.
    """
    counts = {key: 0 for key in STATUS_KEYS}
    rows = query.with_entities(Report.status, func.count(Report.id)).group_by(Report.status).all()

    total = 0
    for status, quantity in rows:
        counts[status] = quantity
        total += quantity

    counts["total"] = total
    return counts


def _compute_resolution_metrics(reports: Iterable[Report]) -> Dict[str, Optional[float]]:
    """
    Calcula o tempo médio de resolução considerando chamados concluídos.
    """
    resolved = [
        report
        for report in reports
        if report.completed_at and report.created_at
    ]

    if not resolved:
        return {"average_seconds": None, "resolved_count": 0}

    total_seconds = sum(
        (report.completed_at - report.created_at).total_seconds()
        for report in resolved
    )

    return {
        "average_seconds": total_seconds / len(resolved),
        "resolved_count": len(resolved),
    }


def _build_heatmap_points(reports: Iterable[Report], precision: int = 3) -> List[Dict[str, object]]:
    """
    Agrupa chamados por proximidade geográfica para destacar regiões críticas.
    """
    clusters = defaultdict(lambda: {"sum_lat": 0.0, "sum_lng": 0.0, "count": 0})

    for report in reports:
        if report.lat is None or report.lng is None:
            continue

        key = (round(report.lat, precision), round(report.lng, precision))
        cluster = clusters[key]
        cluster["sum_lat"] += report.lat
        cluster["sum_lng"] += report.lng
        cluster["count"] += 1

    points = []
    for (rounded_lat, rounded_lng), values in clusters.items():
        points.append({
            "lat": values["sum_lat"] / values["count"],
            "lng": values["sum_lng"] / values["count"],
            "count": values["count"],
            "label": f"{rounded_lat:.3f}, {rounded_lng:.3f}",
        })

    points.sort(key=lambda item: item["count"], reverse=True)
    return points


def get_citizen_dashboard_data(user: User) -> Dict[str, object]:
    """Dados para o dashboard do cidadão."""
    if not user.is_citizen:
        raise DashboardError("Acesso negado para dashboard de cidadão.")

    base_query = Report.query.filter_by(user_id=user.id)
    reports = base_query.order_by(Report.created_at.desc()).all()
    stats = _status_summary(base_query)

    return {
        "reports": reports,
        "stats": stats,
    }


def get_agency_dashboard_data(
    user: User,
    status_filter: Optional[str] = None,
    category_filter: Optional[str] = None,
) -> Dict[str, object]:
    """Dados para o dashboard de órgãos competentes."""
    if not user.is_agency:
        raise DashboardError("Apenas órgãos podem acessar este dashboard.")

    municipio_id = user.municipio_ibge_id
    if not municipio_id:
        raise DashboardError("Órgão sem município configurado.")

    citizens_query = User.query.filter_by(
        user_type="cidadao",
        is_approved=False,
        is_active=True,
        municipio_origem_id=municipio_id,
    ).order_by(User.created_at.desc())
    pending_citizens = citizens_query.all()

    base_reports_query = Report.query.filter_by(municipio_ibge_id=municipio_id)

    stats = _status_summary(base_reports_query)
    stats["cidadaos_pendentes"] = len(pending_citizens)

    filtered_reports_query = base_reports_query
    if status_filter:
        filtered_reports_query = filtered_reports_query.filter_by(status=status_filter)
    if category_filter:
        filtered_reports_query = filtered_reports_query.filter_by(category=category_filter)

    reports = filtered_reports_query.order_by(Report.created_at.asc()).all()

    municipality_reports = (
        Report.query
        .filter_by(municipio_ibge_id=municipio_id)
        .order_by(Report.created_at.asc())
        .all()
    )

    resolution_metrics = _compute_resolution_metrics(municipality_reports)
    heat_points = _build_heatmap_points(municipality_reports)
    hot_regions = heat_points[:5]

    return {
        "reports": reports,
        "stats": stats,
        "pending_citizens": pending_citizens,
        "filters": {
            "status": status_filter,
            "category": category_filter,
        },
        "resolution_metrics": resolution_metrics,
        "heat_points": heat_points,
        "hot_regions": hot_regions,
    }


def get_admin_dashboard_data(admin: User, filter_type: str = "pending") -> Dict[str, object]:
    """Dados para o dashboard administrativo."""
    if not admin.is_admin:
        raise DashboardError("Apenas administradores podem acessar este dashboard.")

    filter_type = filter_type or "pending"

    query = User.query.filter(User.id != admin.id)
    if filter_type == "pending":
        query = query.filter_by(is_approved=False, is_admin=False)
    elif filter_type == "approved":
        query = query.filter_by(is_approved=True)

    users = query.order_by(User.created_at.desc()).all()

    stats_row = (
        db.session.query(
            func.count(User.id).label("total"),
            func.sum(case((User.is_approved == False, 1), else_=0)).label("pending"),  # noqa: E712
            func.sum(case((User.is_approved == True, 1), else_=0)).label("approved"),  # noqa: E712
            func.sum(case((User.user_type == "cidadao", 1), else_=0)).label("citizens"),
            func.sum(case((User.user_type == "orgao", 1), else_=0)).label("agencies"),
        )
        .filter(User.id != admin.id)
        .one()
    )

    stats = {
        "total": stats_row.total or 0,
        "pending": stats_row.pending or 0,
        "approved": stats_row.approved or 0,
        "citizens": stats_row.citizens or 0,
        "agencies": stats_row.agencies or 0,
    }

    return {
        "users": users,
        "stats": stats,
        "filter_type": filter_type,
    }
