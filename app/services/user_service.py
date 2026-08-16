"""
Serviços auxiliares para ações administrativas sobre usuários.
"""
from __future__ import annotations

from typing import Optional
from django.utils import timezone

from core.models import ApprovalRequest, User
from app.services.email_service import send_approval_email


class UserActionError(Exception):
    """Erro para ações inválidas sobre usuários."""


def update_user_profile_by_admin(user: User, admin: User, payload: dict) -> None:
    if not admin.is_admin:
        raise UserActionError('Somente administradores podem editar perfis.')
    if user.is_platform_owner and admin.id != user.id:
        raise UserActionError('Não é possível editar o perfil do dono da plataforma.')

    name = (payload.get('name') or '').strip()
    email_raw = (payload.get('email') or '').strip().lower()
    telefone = (payload.get('telefone') or '').strip() or None

    if not name:
        raise UserActionError('Nome é obrigatório.')

    if email_raw:
        if User.objects.filter(email=email_raw).exclude(pk=user.pk).exists():
            raise UserActionError('Este email já está em uso por outro usuário.')
        user.email = email_raw
    else:
        user.email = None

    user.name = name
    user.telefone = telefone

    if user.user_type == 'orgao':
        user.orgao_nome = (payload.get('orgao_nome') or '').strip() or user.orgao_nome
        municipio_ibge_id_raw = (payload.get('municipio_ibge_id') or '').strip()
        if municipio_ibge_id_raw:
            try:
                user.municipio_ibge_id = int(municipio_ibge_id_raw)
            except ValueError as exc:
                raise UserActionError('ID do município do órgão inválido.') from exc
        user.municipio_nome = (payload.get('municipio_nome') or '').strip() or user.municipio_nome
        user.municipio_uf = (payload.get('municipio_uf') or '').strip().upper() or user.municipio_uf

    if user.user_type == 'cidadao':
        municipio_origem_id_raw = (payload.get('municipio_origem_id') or '').strip()
        if municipio_origem_id_raw:
            try:
                user.municipio_origem_id = int(municipio_origem_id_raw)
            except ValueError as exc:
                raise UserActionError('ID do município de origem inválido.') from exc
        user.municipio_origem_nome = (payload.get('municipio_origem_nome') or '').strip() or user.municipio_origem_nome
        user.municipio_origem_uf = (payload.get('municipio_origem_uf') or '').strip().upper() or user.municipio_origem_uf

    user.save()


def approve_user_by_admin(user: User, approver: User) -> None:
    if not approver.is_admin:
        raise UserActionError('Somente administradores podem aprovar usuários.')
    if user.is_platform_owner and approver.id != user.id:
        raise UserActionError('Não é possível alterar o dono da plataforma.')
    if user.is_admin and not approver.is_platform_owner and approver.id != user.id:
        raise UserActionError('Somente o dono da plataforma pode alterar outro administrador.')
    if user.is_approved:
        raise UserActionError('Usuário já está aprovado.')

    user.is_approved = True
    user.is_active = True
    user.approved_by = approver
    user.approved_at = timezone.now()
    user.save()

    if user.email:
        send_approval_email(user)


def reject_user_by_admin(user: User, approver: User) -> None:
    if not approver.is_admin:
        raise UserActionError('Somente administradores podem rejeitar usuários.')
    if user.is_platform_owner and approver.id != user.id:
        raise UserActionError('Não é possível desativar o dono da plataforma.')
    if user.is_admin and not approver.is_platform_owner and approver.id != user.id:
        raise UserActionError('Somente o dono da plataforma pode desativar outro administrador.')

    user.is_active = False
    user.is_approved = False
    user.save()


def activate_user_by_admin(user: User, approver: User) -> None:
    if not approver.is_admin:
        raise UserActionError('Somente administradores podem reativar usuários.')
    if user.is_platform_owner and approver.id != user.id:
        raise UserActionError('Não é possível alterar o dono da plataforma.')
    if user.is_admin and not approver.is_platform_owner and approver.id != user.id:
        raise UserActionError('Somente o dono da plataforma pode reativar outro administrador.')

    user.is_active = True
    user.save()


def approve_citizen_by_agency(citizen: User, agency: User) -> None:
    if not agency.is_agency:
        raise UserActionError('Somente órgãos podem aprovar cidadãos.')
    if not citizen.is_citizen:
        raise UserActionError('Somente cidadãos podem ser aprovados por órgãos.')
    if citizen.municipio_origem_id != agency.municipio_ibge_id:
        raise UserActionError('Cidadão pertence a outro município.')
    if citizen.is_approved:
        raise UserActionError('Cidadão já está aprovado.')

    citizen.is_approved = True
    citizen.is_active = True
    citizen.approved_by = agency
    citizen.approved_at = timezone.now()
    citizen.save()

    pending_request = ApprovalRequest.objects.filter(user=citizen, status='pending').first()
    if pending_request:
        pending_request.status = 'approved'
        pending_request.agency = agency
        pending_request.resolved_at = timezone.now()
        pending_request.save()

    if citizen.email:
        send_approval_email(citizen)


def reject_citizen_by_agency(citizen: User, agency: User, reason: Optional[str] = None) -> None:
    if not agency.is_agency:
        raise UserActionError('Somente órgãos podem rejeitar cidadãos.')
    if not citizen.is_citizen:
        raise UserActionError('Somente cidadãos podem ser rejeitados por órgãos.')
    if citizen.municipio_origem_id != agency.municipio_ibge_id:
        raise UserActionError('Cidadão pertence a outro município.')

    citizen.is_active = False
    citizen.is_approved = False
    citizen.save()

    pending_request = ApprovalRequest.objects.filter(user=citizen, status='pending').first()
    if pending_request:
        pending_request.status = 'rejected'
        pending_request.agency = agency
        pending_request.rejection_reason = reason or 'Não informado'
        pending_request.resolved_at = timezone.now()
        pending_request.save()
