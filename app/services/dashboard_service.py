"""
Serviço de agregação de dados para os dashboards da aplicação.
Concentra consultas e cálculos de estatísticas em um único lugar.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

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

    reports_query = Report.query.filter_by(municipio_ibge_id=municipio_id)
    if status_filter:
        reports_query = reports_query.filter_by(status=status_filter)
    if category_filter:
        reports_query = reports_query.filter_by(category=category_filter)

    reports = reports_query.order_by(Report.created_at.asc()).all()

    stats = _status_summary(Report.query.filter_by(municipio_ibge_id=municipio_id))
    stats["cidadaos_pendentes"] = len(pending_citizens)

    return {
        "reports": reports,
        "stats": stats,
        "pending_citizens": pending_citizens,
        "filters": {
            "status": status_filter,
            "category": category_filter,
        },
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

