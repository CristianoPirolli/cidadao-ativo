"""
Serviços auxiliares para ações administrativas/comerciais sobre usuários.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from app.models.models import ApprovalRequest, User, db
from app.services.email_service import send_approval_email


class UserActionError(Exception):
    """Erro para ações inválidas sobre usuários."""


def approve_user_by_admin(user: User, approver: User) -> None:
    """Aprova um usuário qualquer via administrador."""
    if not approver.is_admin:
        raise UserActionError("Somente administradores podem aprovar usuários.")

    if user.is_admin:
        raise UserActionError("Não é possível alterar outro administrador.")

    if user.is_approved:
        raise UserActionError("Usuário já está aprovado.")

    user.is_approved = True
    user.is_active = True
    user.approved_by = approver.id
    user.approved_at = datetime.utcnow()
    db.session.commit()

    if user.email:
        send_approval_email(user)


def reject_user_by_admin(user: User, approver: User) -> None:
    """Rejeita/desativa um usuário via administrador."""
    if not approver.is_admin:
        raise UserActionError("Somente administradores podem rejeitar usuários.")

    if user.is_admin:
        raise UserActionError("Não é possível rejeitar um administrador.")

    user.is_active = False
    user.is_approved = False
    db.session.commit()


def activate_user_by_admin(user: User, approver: User) -> None:
    """Reativa um usuário inativo via administrador."""
    if not approver.is_admin:
        raise UserActionError("Somente administradores podem reativar usuários.")

    if user.is_admin and approver.id != user.id:
        raise UserActionError("Somente o próprio admin pode reativar sua conta.")

    user.is_active = True
    db.session.commit()


def approve_citizen_by_agency(citizen: User, agency: User) -> None:
    """Órgão aprova o cadastro de um cidadão."""
    if not agency.is_agency:
        raise UserActionError("Somente órgãos podem aprovar cidadãos.")

    if not citizen.is_citizen:
        raise UserActionError("Somente cidadãos podem ser aprovados por órgãos.")

    if citizen.municipio_origem_id != agency.municipio_ibge_id:
        raise UserActionError("Cidadão pertence a outro município.")

    if citizen.is_approved:
        raise UserActionError("Cidadão já está aprovado.")

    citizen.is_approved = True
    citizen.is_active = True
    citizen.approved_by = agency.id
    citizen.approved_at = datetime.utcnow()

    pending_request = ApprovalRequest.query.filter_by(
        user_id=citizen.id,
        status="pending",
    ).first()

    if pending_request:
        pending_request.status = "approved"
        pending_request.agency_id = agency.id
        pending_request.resolved_at = datetime.utcnow()

    db.session.commit()

    if citizen.email:
        send_approval_email(citizen)


def reject_citizen_by_agency(citizen: User, agency: User, reason: Optional[str] = None) -> None:
    """Órgão rejeita o cadastro de um cidadão."""
    if not agency.is_agency:
        raise UserActionError("Somente órgãos podem rejeitar cidadãos.")

    if not citizen.is_citizen:
        raise UserActionError("Somente cidadãos podem ser rejeitados por órgãos.")

    if citizen.municipio_origem_id != agency.municipio_ibge_id:
        raise UserActionError("Cidadão pertence a outro município.")

    citizen.is_active = False
    citizen.is_approved = False

    pending_request = ApprovalRequest.query.filter_by(
        user_id=citizen.id,
        status="pending",
    ).first()

    if pending_request:
        pending_request.status = "rejected"
        pending_request.agency_id = agency.id
        pending_request.rejection_reason = reason or "Não informado"
        pending_request.resolved_at = datetime.utcnow()

    db.session.commit()

