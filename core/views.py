"""
Views Django — equivalente ao view_routes.py do Flask
"""
import os
from datetime import datetime, timezone as dt_timezone

from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.conf import settings

from core.models import OuvidoriaMessage, Report, ReportHistory, ReportUrgencyVote, User
from app.services.auth_service import AuthenticationError, RegistrationError, authenticate_user, register_user
from app.services.dashboard_service import DashboardError, get_admin_dashboard_data, get_agency_dashboard_data, get_citizen_dashboard_data
from app.services.user_service import (
    UserActionError,
    activate_user_by_admin,
    approve_citizen_by_agency,
    approve_user_by_admin,
    reject_citizen_by_agency,
    reject_user_by_admin,
    update_user_profile_by_admin,
)
from app.services.ouvidoria_service import OuvidoriaValidationError, validate_ouvidoria_message


def _get_user_municipio_context(user):
    if user.is_citizen:
        return user.municipio_origem_id, user.municipio_origem_nome, user.municipio_origem_uf
    if user.is_agency:
        return user.municipio_ibge_id, user.municipio_nome, user.municipio_uf
    return None, None, None


def index(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'welcome.html')


@login_required
def denuncia(request):
    return render(request, 'index.html')


@login_required
def dashboard(request):
    user = request.user
    if user.is_admin:
        return redirect('dashboard_admin')
    elif user.is_citizen:
        return redirect('dashboard_citizen')
    elif user.is_agency:
        return redirect('dashboard_agency')
    messages.error(request, 'Tipo de usuário não reconhecido')
    return redirect('index')


@login_required
def ouvidoria(request):
    selected_municipio = request.GET.get('municipio_id', type(0).__new__(type(0))) or None
    if selected_municipio is not None:
        try:
            selected_municipio = int(selected_municipio)
        except (ValueError, TypeError):
            selected_municipio = None
    show_inactive = request.GET.get('show_inactive', '0') == '1'

    if request.method == 'POST':
        municipio_id, municipio_nome, municipio_uf = _get_user_municipio_context(request.user)
        if not municipio_id:
            messages.error(request, 'Seu usuário não possui município associado para publicar na ouvidoria.')
            return redirect('ouvidoria')

        content = request.POST.get('content', '')
        try:
            clean_content, _ = validate_ouvidoria_message(content)
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
        if request.user.is_platform_owner:
            if not show_inactive:
                messages_qs = messages_qs.filter(is_active=True)
        else:
            messages_qs = messages_qs.filter(is_active=True)
    else:
        municipio_id, _, _ = _get_user_municipio_context(request.user)
        if not municipio_id:
            messages.error(request, 'Seu usuário não possui município associado para acessar a ouvidoria.')
            return redirect('dashboard')
        messages_qs = messages_qs.filter(municipio_ibge_id=municipio_id, is_active=True)

    ouvidoria_msgs = messages_qs.select_related('user').order_by('-created_at')[:100]
    return render(request, 'ouvidoria.html', {
        'messages_list': ouvidoria_msgs,
        'selected_municipio': selected_municipio,
        'available_municipios': available_municipios,
        'show_inactive': show_inactive,
    })


@login_required
def inativar_mensagem_ouvidoria(request, message_id):
    if not request.user.is_platform_owner:
        messages.error(request, 'Somente o dono da plataforma pode inativar mensagens da ouvidoria.')
        return redirect('ouvidoria')
    msg = get_object_or_404(OuvidoriaMessage, pk=message_id)
    if not msg.is_active:
        messages.info(request, 'Mensagem já está inativa.')
        return redirect('ouvidoria')
    msg.is_active = False
    msg.moderator = request.user
    msg.moderated_at = timezone.now()
    msg.save()
    messages.success(request, 'Mensagem inativada com sucesso.')
    return redirect('ouvidoria')


@login_required
def reativar_mensagem_ouvidoria(request, message_id):
    if not request.user.is_platform_owner:
        messages.error(request, 'Somente o dono da plataforma pode reativar mensagens da ouvidoria.')
        return redirect('ouvidoria')
    msg = get_object_or_404(OuvidoriaMessage, pk=message_id)
    if msg.is_active:
        messages.info(request, 'Mensagem já está ativa.')
        return redirect('ouvidoria')
    msg.is_active = True
    msg.moderator = request.user
    msg.moderated_at = timezone.now()
    msg.save()
    messages.success(request, 'Mensagem reativada com sucesso.')
    return redirect('ouvidoria')


@login_required
def dashboard_citizen(request):
    if not request.user.is_citizen:
        messages.error(request, 'Acesso negado. Área exclusiva para cidadãos.')
        return redirect('dashboard')
    try:
        data = get_citizen_dashboard_data(request.user)
    except DashboardError as exc:
        messages.error(request, str(exc))
        return redirect('dashboard')
    return render(request, 'dashboard_citizen.html', {
        'reports': data['reports'],
        'stats': data['stats'],
        'voted_report_ids': data.get('voted_report_ids', set()),
    })


@login_required
def dashboard_agency(request):
    if not request.user.is_agency:
        messages.error(request, 'Acesso negado. Área exclusiva para órgãos competentes.')
        return redirect('dashboard')

    status_filter = request.GET.get('status') or None
    category_filter = request.GET.get('category') or None

    try:
        data = get_agency_dashboard_data(request.user, status_filter=status_filter, category_filter=category_filter)
    except DashboardError as exc:
        messages.error(request, str(exc))
        return redirect('index')

    map_reports = []
    for report in data['reports']:
        if report.lat is None or report.lng is None:
            continue
        map_reports.append({
            'id': report.id,
            'title': report.title,
            'category': report.category,
            'status': report.status_display,
            'status_raw': report.status,
            'lat': report.lat,
            'lng': report.lng,
            'created_at': report.created_at.strftime('%d/%m/%Y %H:%M') if report.created_at else '-',
            'detail_url': f'/report/{report.id}',
        })

    map_bounds = None
    map_center = None
    if map_reports:
        latitudes = [item['lat'] for item in map_reports]
        longitudes = [item['lng'] for item in map_reports]
        padding = 0.02

        def _clamp(value, min_v, max_v):
            return max(min_v, min(value, max_v))

        map_bounds = {
            'southWest': {
                'lat': _clamp(min(latitudes) - padding, -90, 90),
                'lng': _clamp(min(longitudes) - padding, -180, 180),
            },
            'northEast': {
                'lat': _clamp(max(latitudes) + padding, -90, 90),
                'lng': _clamp(max(longitudes) + padding, -180, 180),
            },
        }
        map_center = {
            'lat': sum(latitudes) / len(latitudes),
            'lng': sum(longitudes) / len(longitudes),
        }

    return render(request, 'dashboard_agency.html', {
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


@login_required
def dashboard_admin(request):
    if not request.user.is_admin:
        messages.error(request, 'Acesso negado. Área exclusiva para administradores.')
        return redirect('dashboard')

    filter_type = request.GET.get('filter', 'pending')
    try:
        data = get_admin_dashboard_data(request.user, filter_type=filter_type)
    except DashboardError as exc:
        messages.error(request, str(exc))
        return redirect('dashboard')

    return render(request, 'dashboard_admin.html', {
        'users': data['users'],
        'stats': data['stats'],
        'report_stats': data['report_stats'],
        'recent_reports': data['recent_reports'],
        'filter_type': data['filter_type'],
    })


@login_required
def edit_user_by_admin(request, user_id):
    if not request.user.is_admin:
        messages.error(request, 'Acesso negado. Área exclusiva para administradores.')
        return redirect('dashboard')
    user = get_object_or_404(User, pk=user_id)
    if request.method == 'POST':
        try:
            update_user_profile_by_admin(user, request.user, request.POST)
        except UserActionError as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, f'Perfil de {user.name} atualizado com sucesso.')
            return redirect(f'/dashboard/admin?filter=all')
    return render(request, 'admin_edit_user.html', {'user': user})


@login_required
def approve_user(request, user_id):
    if not request.user.is_admin:
        messages.error(request, 'Acesso negado. Área exclusiva para administradores.')
        return redirect('dashboard')
    user = get_object_or_404(User, pk=user_id)
    try:
        approve_user_by_admin(user, request.user)
    except UserActionError as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, f'Usuário {user.name} aprovado com sucesso!')
    return redirect('dashboard_admin')


@login_required
def reject_user(request, user_id):
    if not request.user.is_admin:
        messages.error(request, 'Acesso negado. Área exclusiva para administradores.')
        return redirect('dashboard')
    user = get_object_or_404(User, pk=user_id)
    try:
        reject_user_by_admin(user, request.user)
    except UserActionError as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, f'Usuário {user.name} desativado com sucesso!')
    return redirect('dashboard_admin')


@login_required
def activate_user(request, user_id):
    if not request.user.is_admin:
        messages.error(request, 'Acesso negado. Área exclusiva para administradores.')
        return redirect('dashboard')
    user = get_object_or_404(User, pk=user_id)
    try:
        activate_user_by_admin(user, request.user)
    except UserActionError as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, f'Usuário {user.name} reativado com sucesso!')
    return redirect('dashboard_admin')


@login_required
def agency_approve_citizen(request, user_id):
    if not request.user.is_agency:
        messages.error(request, 'Acesso negado. Área exclusiva para órgãos.')
        return redirect('dashboard')
    citizen = get_object_or_404(User, pk=user_id)
    try:
        approve_citizen_by_agency(citizen, request.user)
    except UserActionError as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, f'Cidadão {citizen.name} aprovado com sucesso!')
    return redirect('dashboard')


@login_required
def agency_reject_citizen(request, user_id):
    if not request.user.is_agency:
        messages.error(request, 'Acesso negado. Área exclusiva para órgãos.')
        return redirect('dashboard')
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
    if not request.user.is_agency and not request.user.is_admin:
        messages.error(request, 'Acesso negado.')
        return redirect('dashboard')
    citizen = get_object_or_404(User, pk=user_id)
    if request.user.is_agency and citizen.municipio_origem_id != request.user.municipio_ibge_id:
        messages.error(request, 'Você só pode visualizar comprovantes de cidadãos do seu município')
        return redirect('dashboard')
    if not citizen.residence_proof_path:
        messages.error(request, 'Este cidadão não possui comprovante de residência')
        return redirect('dashboard')

    full_path = os.path.join(settings.MEDIA_ROOT, citizen.residence_proof_path)
    if not os.path.exists(full_path):
        raise Http404('Arquivo não encontrado')
    return FileResponse(open(full_path, 'rb'))


@login_required
def report_detail(request, report_id):
    report = get_object_or_404(Report.objects.select_related('user', 'assigned_user'), pk=report_id)
    user = request.user

    if user.is_citizen:
        same_city = (
            user.municipio_origem_id is not None
            and report.municipio_ibge_id == user.municipio_origem_id
        )
        is_owner = report.user_id == user.id
        if not same_city and not is_owner:
            messages.error(request, 'Você não tem permissão para visualizar este chamado')
            return redirect('dashboard')

    history = ReportHistory.objects.filter(report=report).select_related('user').order_by('created_at')

    if user.is_agency and not report.viewed_at:
        report.viewed_at = timezone.now()
        report.save(update_fields=['viewed_at'])
        ReportHistory.objects.create(
            report=report,
            user=user,
            action='visualizado',
            old_status=report.status,
            new_status=report.status,
            comment='Chamado visualizado pelo órgão responsável',
        )

    has_voted_urgency = False
    if user.is_citizen:
        has_voted_urgency = ReportUrgencyVote.objects.filter(report=report, user=user).exists()

    return render(request, 'report_detail.html', {
        'report': report,
        'history': history,
        'has_voted_urgency': has_voted_urgency,
    })


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        login_id = request.POST.get('login_id') or request.POST.get('email', '')
        password = request.POST.get('password', '')
        try:
            user = authenticate_user(login_id, password)
        except AuthenticationError as exc:
            message = str(exc)
            category = messages.WARNING if 'aprov' in message.lower() else messages.ERROR
            messages.add_message(request, category, message)
        else:
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            next_page = request.GET.get('next')
            return redirect(next_page or 'dashboard')
    return render(request, 'login.html')


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        try:
            result = register_user(request.POST, request.FILES)
        except RegistrationError as exc:
            for error in exc.messages:
                messages.error(request, error)
            return render(request, 'register.html')
        messages.add_message(request, messages.SUCCESS if result.flash_category == 'success' else messages.INFO, result.message)
        return redirect('login')
    return render(request, 'register.html')


def logout_view(request):
    logout(request)
    messages.info(request, 'Você saiu da sua conta')
    return redirect('index')


def qr_demo(request):
    demo_url = os.environ.get('DEMO_PUBLIC_URL', None)
    qr_code_path = os.path.join(settings.BASE_DIR, 'app', 'static', 'qr_code_demo.png')
    qr_code_exists = os.path.exists(qr_code_path)
    return render(request, 'qr_demo.html', {
        'demo_url': demo_url,
        'qr_code_exists': qr_code_exists,
    })


@login_required
def dashboard_owner(request):
    if not request.user.is_platform_owner:
        messages.error(request, 'Acesso restrito ao dono da plataforma.')
        return redirect('dashboard')

    tab = request.GET.get('tab', 'agencies')

    pending_agencies = User.objects.filter(
        user_type='orgao', is_approved=False, is_active=True
    ).order_by('created_at')

    all_admins = User.objects.filter(is_admin=True).order_by('name')

    all_agencies = User.objects.filter(user_type='orgao').order_by('-created_at')

    from core.models import Report
    from django.db.models import Count, Q
    platform_stats = {
        'total_users': User.objects.count(),
        'total_agencies': User.objects.filter(user_type='orgao').count(),
        'pending_agencies': User.objects.filter(user_type='orgao', is_approved=False, is_active=True).count(),
        'total_citizens': User.objects.filter(user_type='cidadao').count(),
        'total_admins': User.objects.filter(is_admin=True).count(),
        'total_reports': Report.objects.count(),
        'open_reports': Report.objects.filter(status='aberto').count(),
        'resolved_reports': Report.objects.filter(status='resolvido').count(),
        'municipalities': Report.objects.values('municipio_ibge_id').distinct().count(),
    }

    return render(request, 'dashboard_owner.html', {
        'tab': tab,
        'pending_agencies': pending_agencies,
        'all_admins': all_admins,
        'all_agencies': all_agencies,
        'platform_stats': platform_stats,
    })


@login_required
def reset_user_password(request, user_id):
    if not request.user.is_platform_owner:
        messages.error(request, 'Acesso restrito ao dono da plataforma.')
        return redirect('dashboard')
    if request.method != 'POST':
        return redirect('edit_user_by_admin', user_id=user_id)

    target = get_object_or_404(User, pk=user_id)
    new_password = request.POST.get('new_password', '')
    confirm_password = request.POST.get('confirm_password', '')

    if len(new_password) < 8:
        messages.error(request, 'A senha deve ter pelo menos 8 caracteres.')
        return redirect('edit_user_by_admin', user_id=user_id)

    if new_password != confirm_password:
        messages.error(request, 'As senhas não coincidem.')
        return redirect('edit_user_by_admin', user_id=user_id)

    target.set_password(new_password)
    target.save()
    messages.success(request, f'Senha de {target.name} resetada com sucesso.')
    return redirect('edit_user_by_admin', user_id=user_id)


@login_required
def toggle_admin(request, user_id):
    if not request.user.is_platform_owner:
        messages.error(request, 'Acesso restrito ao dono da plataforma.')
        return redirect('dashboard')
    if request.method != 'POST':
        return redirect('dashboard_owner')

    target = get_object_or_404(User, pk=user_id)

    if target.is_platform_owner:
        messages.error(request, 'Não é possível alterar o nível do dono da plataforma.')
        return redirect('dashboard_owner')

    if target.is_admin:
        target.is_admin = False
        target.save()
        messages.success(request, f'{target.name} removido do nível de admin.')
    else:
        target.is_admin = True
        target.is_approved = True
        target.save()
        messages.success(request, f'{target.name} promovido a admin com sucesso.')

    return redirect(f'/dashboard/owner?tab=admins')
