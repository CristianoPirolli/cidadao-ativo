"""Autenticação, cadastro e gestão de usuários."""
import os

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit

from apps.accounts.models import User
from apps.accounts.services.auth import (
    AuthenticationError,
    RegistrationError,
    authenticate_user,
    register_user,
)
from apps.accounts.services.users import (
    UserActionError,
    activate_user_by_admin,
    approve_citizen_by_agency,
    approve_user_by_admin,
    reject_citizen_by_agency,
    reject_user_by_admin,
    update_user_profile_by_admin,
)
from apps.core.decorators import admin_required, agency_required, owner_required

# ── Autenticação ────────────────────────────────────────────────────────────

@ratelimit(key='ip', rate='10/m', method='POST', block=False)
def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        if getattr(request, 'limited', False):
            messages.error(request, 'Muitas tentativas de login. Aguarde um minuto e tente novamente.')
            return render(request, 'accounts/login.html', status=429)

        login_id = request.POST.get('login_id') or request.POST.get('email', '')
        password = request.POST.get('password', '')
        try:
            user = authenticate_user(login_id, password)
        except AuthenticationError as exc:
            message = str(exc)
            level = messages.WARNING if 'aprov' in message.lower() else messages.ERROR
            messages.add_message(request, level, message)
        else:
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            next_page = request.GET.get('next')
            if next_page and url_has_allowed_host_and_scheme(
                next_page, allowed_hosts={request.get_host()}, require_https=request.is_secure()
            ):
                return redirect(next_page)
            return redirect('dashboard')

    return render(request, 'accounts/login.html')


@ratelimit(key='ip', rate='5/m', method='POST', block=False)
def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        if getattr(request, 'limited', False):
            messages.error(request, 'Muitas tentativas de cadastro. Aguarde um minuto e tente novamente.')
            return render(request, 'accounts/register.html', status=429)
        try:
            result = register_user(request.POST, request.FILES)
        except RegistrationError as exc:
            for error in exc.messages:
                messages.error(request, error)
            return render(request, 'accounts/register.html')
        level = messages.SUCCESS if result.flash_category == 'success' else messages.INFO
        messages.add_message(request, level, result.message)
        return redirect('login')

    return render(request, 'accounts/register.html')


def logout_view(request):
    logout(request)
    messages.info(request, 'Você saiu da sua conta')
    return redirect('index')


# ── Ações de administrador ─────────────────────────────────────────────────

@admin_required
def edit_user_by_admin(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    if request.method == 'POST':
        try:
            update_user_profile_by_admin(user, request.user, request.POST)
        except UserActionError as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, f'Perfil de {user.name} atualizado com sucesso.')
            return redirect(f"{reverse('dashboard_admin')}?filter=all")
    return render(request, 'accounts/admin_edit_user.html', {'user': user})


def _admin_action(request, user_id, action, success_message):
    user = get_object_or_404(User, pk=user_id)
    try:
        action(user, request.user)
    except UserActionError as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, success_message.format(name=user.name))
    return redirect('dashboard_admin')


@admin_required
@require_POST
def approve_user(request, user_id):
    return _admin_action(request, user_id, approve_user_by_admin, 'Usuário {name} aprovado com sucesso!')


@admin_required
@require_POST
def reject_user(request, user_id):
    return _admin_action(request, user_id, reject_user_by_admin, 'Usuário {name} desativado com sucesso!')


@admin_required
@require_POST
def activate_user(request, user_id):
    return _admin_action(request, user_id, activate_user_by_admin, 'Usuário {name} reativado com sucesso!')


# ── Ações do dono da plataforma ────────────────────────────────────────────

@owner_required
@require_POST
def reset_user_password(request, user_id):
    target = get_object_or_404(User, pk=user_id)
    new_password = request.POST.get('new_password', '')
    confirm_password = request.POST.get('confirm_password', '')

    if new_password != confirm_password:
        messages.error(request, 'As senhas não coincidem.')
        return redirect('edit_user_by_admin', user_id=user_id)
    try:
        validate_password(new_password, user=target)
    except ValidationError as exc:
        for error in exc.messages:
            messages.error(request, error)
    else:
        target.set_password(new_password)
        target.save(update_fields=['password'])
        messages.success(request, f'Senha de {target.name} resetada com sucesso.')
    return redirect('edit_user_by_admin', user_id=user_id)


@owner_required
@require_POST
def toggle_admin(request, user_id):
    target = get_object_or_404(User, pk=user_id)

    if target.is_platform_owner:
        messages.error(request, 'Não é possível alterar o nível do dono da plataforma.')
        return redirect('dashboard_owner')

    if target.is_admin:
        target.is_admin = False
        target.save(update_fields=['is_admin'])
        messages.success(request, f'{target.name} removido do nível de admin.')
    else:
        target.is_admin = True
        target.is_approved = True
        target.save(update_fields=['is_admin', 'is_approved'])
        messages.success(request, f'{target.name} promovido a admin com sucesso.')

    return redirect(f"{reverse('dashboard_owner')}?tab=admins")


# ── Ações de órgão ─────────────────────────────────────────────────────────

@agency_required
@require_POST
def agency_approve_citizen(request, user_id):
    citizen = get_object_or_404(User, pk=user_id)
    try:
        approve_citizen_by_agency(citizen, request.user)
    except UserActionError as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, f'Cidadão {citizen.name} aprovado com sucesso!')
    return redirect('dashboard')


@agency_required
@require_POST
def agency_reject_citizen(request, user_id):
    citizen = get_object_or_404(User, pk=user_id)
    rejection_reason = request.POST.get('rejection_reason', 'Não informado')
    try:
        reject_citizen_by_agency(citizen, request.user, rejection_reason)
    except UserActionError as exc:
        messages.error(request, str(exc))
    else:
        messages.info(request, f'Cadastro de {citizen.name} foi rejeitado.')
    return redirect('dashboard')


@login_required
def view_residence_proof(request, user_id):
    if not (request.user.is_agency or request.user.is_admin):
        messages.error(request, 'Acesso negado.')
        return redirect('dashboard')

    citizen = get_object_or_404(User, pk=user_id)
    if request.user.is_agency and citizen.municipio_origem_id != request.user.municipio_ibge_id:
        messages.error(request, 'Você só pode visualizar comprovantes de cidadãos do seu município')
        return redirect('dashboard')
    if not citizen.residence_proof_path:
        messages.error(request, 'Este cidadão não possui comprovante de residência')
        return redirect('dashboard')

    media_root = os.path.realpath(settings.MEDIA_ROOT)
    full_path = os.path.realpath(os.path.join(media_root, citizen.residence_proof_path))
    if not full_path.startswith(media_root + os.sep) or not os.path.exists(full_path):
        raise Http404('Arquivo não encontrado')
    return FileResponse(open(full_path, 'rb'))
