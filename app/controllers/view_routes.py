"""
View Routes - Rotas que renderizam templates HTML
"""
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user

from app.models.models import User, Report, ReportHistory, db
from app.services.auth_service import (
    AuthenticationError,
    RegistrationError,
    authenticate_user,
    register_user,
)
from app.services.dashboard_service import (
    DashboardError,
    get_admin_dashboard_data,
    get_agency_dashboard_data,
    get_citizen_dashboard_data,
)
from app.services.user_service import (
    UserActionError,
    activate_user_by_admin,
    approve_citizen_by_agency,
    approve_user_by_admin,
    reject_citizen_by_agency,
    reject_user_by_admin,
)

views_bp = Blueprint('views', __name__)

@views_bp.route('/')
def index():
    """Pagina inicial - mostra boas-vindas ou redireciona para dashboard"""
    if current_user.is_authenticated:
        return redirect(url_for('views.dashboard'))
    # Mostra página de boas-vindas para visitantes não autenticados
    return render_template('welcome.html')

@views_bp.route('/denuncia')
@login_required
def denuncia():
    """Pagina de formulario de denuncias para cidadaos"""
    return render_template('index.html')

@views_bp.route('/dashboard')
@login_required
def dashboard():
    """Redireciona para o dashboard apropriado baseado no tipo de usuario"""
    if current_user.is_admin:
        return redirect(url_for('views.dashboard_admin'))
    elif current_user.is_citizen:
        return redirect(url_for('views.dashboard_citizen'))
    elif current_user.is_agency:
        return redirect(url_for('views.dashboard_agency'))
    else:
        flash('Tipo de usuario nao reconhecido', 'error')
        return redirect(url_for('views.index'))

@views_bp.route('/dashboard/cidadao')
@login_required
def dashboard_citizen():
    """Dashboard do cidadao - visualiza seus proprios chamados"""
    if not current_user.is_citizen:
        flash('Acesso negado. Area exclusiva para cidadaos.', 'error')
        return redirect(url_for('views.dashboard'))

    try:
        data = get_citizen_dashboard_data(current_user)
    except DashboardError as exc:
        flash(str(exc), 'error')
        return redirect(url_for('views.dashboard'))

    return render_template(
        'dashboard_citizen.html',
        reports=data['reports'],
        stats=data['stats'],
    )

@views_bp.route('/dashboard/orgao')
@login_required
def dashboard_agency():
    """Dashboard do orgao - visualiza chamados e cidadaos do seu municipio"""
    if not current_user.is_agency:
        flash('Acesso negado. Area exclusiva para orgaos competentes.', 'error')
        return redirect(url_for('views.dashboard'))

    status_filter = request.args.get('status', None)
    category_filter = request.args.get('category', None)

    try:
        data = get_agency_dashboard_data(
            current_user,
            status_filter=status_filter,
            category_filter=category_filter,
        )
    except DashboardError as exc:
        flash(str(exc), 'error')
        return redirect(url_for('views.index'))

    map_reports = []
    for report in data['reports']:
        if report.lat is None or report.lng is None:
            continue
        map_reports.append({
            "id": report.id,
            "title": report.title,
            "category": report.category,
            "status": report.status_display,
            "status_raw": report.status,
            "lat": report.lat,
            "lng": report.lng,
            "created_at": report.created_at.strftime('%d/%m/%Y %H:%M') if report.created_at else '-',
            "detail_url": url_for('views.report_detail', report_id=report.id),
        })

    map_bounds = None
    map_center = None
    if map_reports:
        latitudes = [item["lat"] for item in map_reports]
        longitudes = [item["lng"] for item in map_reports]
        padding = 0.02
        def _clamp(value, min_value, max_value):
            return max(min_value, min(value, max_value))

        map_bounds = {
            "southWest": {
                "lat": _clamp(min(latitudes) - padding, -90, 90),
                "lng": _clamp(min(longitudes) - padding, -180, 180),
            },
            "northEast": {
                "lat": _clamp(max(latitudes) + padding, -90, 90),
                "lng": _clamp(max(longitudes) + padding, -180, 180),
            },
        }
        map_center = {
            "lat": sum(latitudes) / len(latitudes),
            "lng": sum(longitudes) / len(longitudes),
        }

    return render_template(
        'dashboard_agency.html',
        reports=data['reports'],
        stats=data['stats'],
        pending_citizens=data['pending_citizens'],
        filters=data['filters'],
        map_reports=map_reports,
        map_bounds=map_bounds,
        map_center=map_center,
    )

# Manter compatibilidade com rota antiga
@views_bp.route('/admin')
@login_required
def admin():
    """Redireciona para o dashboard apropriado"""
    return redirect(url_for('views.dashboard'))

@views_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Pagina e logica de login - Cidadaos usam CPF, Orgaos e Admin usam email"""
    if current_user.is_authenticated:
        return redirect(url_for('views.dashboard'))

    if request.method == 'POST':
        login_id = request.form.get('login_id') or request.form.get('email', '')
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))

        try:
            user = authenticate_user(login_id, password)
        except AuthenticationError as exc:
            message = str(exc)
            category = 'warning' if 'aprov' in message.lower() else 'error'
            flash(message, category)
        else:
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('views.dashboard'))

    return render_template('login.html')

@views_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Fluxo de cadastro com validacoes centralizadas no servico."""
    if current_user.is_authenticated:
        return redirect(url_for('views.dashboard'))

    if request.method == 'POST':
        try:
            result = register_user(request.form, request.files)
        except RegistrationError as exc:
            for error in exc.messages:
                flash(error, 'error')
            return render_template('register.html')

        flash(result.message, result.flash_category)
        return redirect(url_for('views.login'))

    return render_template('register.html')

@views_bp.route('/report/<int:report_id>')
@login_required
def report_detail(report_id):
    """Visualiza detalhes de um report com historico"""
    report = Report.query.get_or_404(report_id)

    # Verificar permissoes
    if current_user.is_citizen and report.user_id != current_user.id:
        flash('Voce nao tem permissao para visualizar este chamado', 'error')
        return redirect(url_for('views.dashboard'))

    # Buscar historico
    history = ReportHistory.query.filter_by(report_id=report_id).order_by(ReportHistory.created_at.asc()).all()

    # Registrar primeira visualizacao sem alterar status
    if current_user.is_agency and not report.viewed_at:
        report.viewed_at = datetime.utcnow()
        history_entry = ReportHistory(
            report_id=report.id,
            user_id=current_user.id,
            action='visualizado',
            old_status=report.status,
            new_status=report.status,
            comment='Chamado visualizado pelo orgao responsavel'
        )
        db.session.add(history_entry)
        db.session.commit()

    return render_template('report_detail.html', report=report, history=history)

@views_bp.route('/dashboard/admin')
@login_required
def dashboard_admin():
    """Dashboard do administrador - gerenciar usuarios"""
    if not current_user.is_admin:
        flash('Acesso negado. Area exclusiva para administradores.', 'error')
        return redirect(url_for('views.dashboard'))

    filter_type = request.args.get('filter', 'pending')  # pending, approved, all

    try:
        data = get_admin_dashboard_data(current_user, filter_type=filter_type)
    except DashboardError as exc:
        flash(str(exc), 'error')
        return redirect(url_for('views.dashboard'))

    return render_template(
        'dashboard_admin.html',
        users=data['users'],
        stats=data['stats'],
        filter_type=data['filter_type'],
    )

@views_bp.route('/admin/approve/<int:user_id>', methods=['POST'])
@login_required
def approve_user(user_id):
    """Aprova um usuario"""
    if not current_user.is_admin:
        flash('Acesso negado. Area exclusiva para administradores.', 'error')
        return redirect(url_for('views.dashboard'))

    user = User.query.get_or_404(user_id)

    try:
        approve_user_by_admin(user, current_user)
    except UserActionError as exc:
        flash(str(exc), 'error')
    else:
        flash(f'Usuario {user.name} aprovado com sucesso!', 'success')
    return redirect(url_for('views.dashboard_admin'))

@views_bp.route('/admin/reject/<int:user_id>', methods=['POST'])
@login_required
def reject_user(user_id):
    """Rejeita/desativa um usuario"""
    if not current_user.is_admin:
        flash('Acesso negado. Area exclusiva para administradores.', 'error')
        return redirect(url_for('views.dashboard'))

    user = User.query.get_or_404(user_id)

    try:
        reject_user_by_admin(user, current_user)
    except UserActionError as exc:
        flash(str(exc), 'error')
    else:
        flash(f'Usuario {user.name} desativado com sucesso!', 'success')
    return redirect(url_for('views.dashboard_admin'))

@views_bp.route('/admin/activate/<int:user_id>', methods=['POST'])
@login_required
def activate_user(user_id):
    """Reativa um usuario"""
    if not current_user.is_admin:
        flash('Acesso negado. Area exclusiva para administradores.', 'error')
        return redirect(url_for('views.dashboard'))

    user = User.query.get_or_404(user_id)

    try:
        activate_user_by_admin(user, current_user)
    except UserActionError as exc:
        flash(str(exc), 'error')
    else:
        flash(f'Usuario {user.name} reativado com sucesso!', 'success')
    return redirect(url_for('views.dashboard_admin'))

@views_bp.route('/orgao/aprovar-cidadao/<int:user_id>', methods=['POST'])
@login_required
def agency_approve_citizen(user_id):
    """Orgao aprova cadastro de cidadao"""
    if not current_user.is_agency:
        flash('Acesso negado. Area exclusiva para orgaos.', 'error')
        return redirect(url_for('views.dashboard'))

    citizen = User.query.get_or_404(user_id)

    try:
        approve_citizen_by_agency(citizen, current_user)
    except UserActionError as exc:
        flash(str(exc), 'error')
    else:
        flash(f'Cidadao {citizen.name} aprovado com sucesso!', 'success')
    return redirect(url_for('views.dashboard'))

@views_bp.route('/orgao/rejeitar-cidadao/<int:user_id>', methods=['POST'])
@login_required
def agency_reject_citizen(user_id):
    """Orgao rejeita cadastro de cidadao"""
    if not current_user.is_agency:
        flash('Acesso negado. Area exclusiva para orgaos.', 'error')
        return redirect(url_for('views.dashboard'))

    citizen = User.query.get_or_404(user_id)

    # Obter motivo da rejeicao
    rejection_reason = request.form.get('rejection_reason', 'Nao informado')

    try:
        reject_citizen_by_agency(citizen, current_user, rejection_reason)
    except UserActionError as exc:
        flash(str(exc), 'error')
    else:
        flash(f'Cadastro de {citizen.name} foi rejeitado.', 'info')
    return redirect(url_for('views.dashboard'))

@views_bp.route('/orgao/comprovante/<int:user_id>')
@login_required
def view_residence_proof(user_id):
    """Visualizar comprovante de residencia de um cidadao"""
    if not current_user.is_agency and not current_user.is_admin:
        flash('Acesso negado.', 'error')
        return redirect(url_for('views.dashboard'))

    citizen = User.query.get_or_404(user_id)

    # Orgaos so podem ver comprovantes de cidadaos do seu municipio
    if current_user.is_agency and citizen.municipio_origem_id != current_user.municipio_ibge_id:
        flash('Voce so pode visualizar comprovantes de cidadaos do seu municipio', 'error')
        return redirect(url_for('views.dashboard'))

    if not citizen.residence_proof_path:
        flash('Este cidadao nao possui comprovante de residencia', 'error')
        return redirect(url_for('views.dashboard'))

    # Servir arquivo
    from flask import send_from_directory
    import os
    upload_dir = current_app.config.get('UPLOAD_FOLDER')
    file_dir = os.path.dirname(os.path.join(upload_dir, citizen.residence_proof_path))
    filename = os.path.basename(citizen.residence_proof_path)

    return send_from_directory(file_dir, filename)

@views_bp.route('/qr-demo')
def qr_demo():
    """Pagina de demonstracao com QR Code para mostra tech"""
    import os
    from flask import send_from_directory

    # Verifica se estamos em modo demo
    demo_url = os.environ.get('DEMO_PUBLIC_URL', None)

    # Caminho do QR Code
    qr_code_path = os.path.join(current_app.root_path, 'static', 'qr_code_demo.png')
    qr_code_exists = os.path.exists(qr_code_path)

    return render_template(
        'qr_demo.html',
        demo_url=demo_url,
        qr_code_exists=qr_code_exists
    )

@views_bp.route('/logout')
@login_required
def logout():
    """Logout do usuario"""
    logout_user()
    flash('Voce saiu da sua conta', 'info')
    return redirect(url_for('views.index'))
