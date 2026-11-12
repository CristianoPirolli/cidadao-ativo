"""Ouvidoria municipal: mural de mensagens por município."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.core.decorators import owner_required
from apps.ouvidoria.models import OuvidoriaMessage
from apps.ouvidoria.services.messages import OuvidoriaValidationError, validate_ouvidoria_message


def _get_user_municipio_context(user):
    if user.is_citizen:
        return user.municipio_origem_id, user.municipio_origem_nome, user.municipio_origem_uf
    if user.is_agency:
        return user.municipio_ibge_id, user.municipio_nome, user.municipio_uf
    return None, None, None


def _parse_int(value):
    try:
        return int(value) if value else None
    except (TypeError, ValueError):
        return None


@login_required
def ouvidoria(request):
    selected_municipio = _parse_int(request.GET.get('municipio_id'))
    show_inactive = request.GET.get('show_inactive', '0') == '1'

    if request.method == 'POST':
        municipio_id, municipio_nome, municipio_uf = _get_user_municipio_context(request.user)
        if not municipio_id:
            messages.error(request, 'Seu usuário não possui município associado para publicar na ouvidoria.')
            return redirect('ouvidoria')

        try:
            clean_content, _ = validate_ouvidoria_message(request.POST.get('content', ''))
        except OuvidoriaValidationError as exc:
            messages.error(request, str(exc))
            return redirect('ouvidoria')

        OuvidoriaMessage.objects.create(
            user=request.user,
            municipio_ibge_id=municipio_id,
            municipio_nome=municipio_nome or 'Município não informado',
            municipio_uf=(municipio_uf or '--').upper(),
            content=clean_content,
        )
        messages.success(request, 'Mensagem publicada na ouvidoria.')
        return redirect('ouvidoria')

    messages_qs = OuvidoriaMessage.objects.all()
    available_municipios = []

    if request.user.is_admin:
        if selected_municipio:
            messages_qs = messages_qs.filter(municipio_ibge_id=selected_municipio)
        available_municipios = (
            OuvidoriaMessage.objects
            .values('municipio_ibge_id', 'municipio_nome', 'municipio_uf')
            .distinct()
            .order_by('municipio_nome')
        )
        if not (request.user.is_platform_owner and show_inactive):
            messages_qs = messages_qs.filter(is_active=True)
    else:
        municipio_id, _, _ = _get_user_municipio_context(request.user)
        if not municipio_id:
            messages.error(request, 'Seu usuário não possui município associado para acessar a ouvidoria.')
            return redirect('dashboard')
        messages_qs = messages_qs.filter(municipio_ibge_id=municipio_id, is_active=True)

    return render(request, 'ouvidoria/ouvidoria.html', {
        'messages_list': messages_qs.select_related('user').order_by('-created_at')[:100],
        'selected_municipio': selected_municipio,
        'available_municipios': available_municipios,
        'show_inactive': show_inactive,
    })


def _set_message_active(request, message_id, active):
    msg = get_object_or_404(OuvidoriaMessage, pk=message_id)
    if msg.is_active == active:
        messages.info(request, f"Mensagem já está {'ativa' if active else 'inativa'}.")
        return redirect('ouvidoria')
    msg.is_active = active
    msg.moderator = request.user
    msg.moderated_at = timezone.now()
    msg.save(update_fields=['is_active', 'moderator', 'moderated_at'])
    messages.success(request, f"Mensagem {'reativada' if active else 'inativada'} com sucesso.")
    return redirect('ouvidoria')


@owner_required
@require_POST
def inativar_mensagem_ouvidoria(request, message_id):
    return _set_message_active(request, message_id, active=False)


@owner_required
@require_POST
def reativar_mensagem_ouvidoria(request, message_id):
    return _set_message_active(request, message_id, active=True)
