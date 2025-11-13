"""
API Routes - Endpoints RESTful para o sistema
"""
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime
import os

from app.models.models import Report, ReportHistory, User, db
from app.services.file_validation import validate_image_file
from app import csrf

api_bp = Blueprint('api', __name__, url_prefix='/api')

# Desabilitar CSRF para todas as rotas da API
csrf.exempt(api_bp)

@api_bp.route('/reports', methods=['GET'])
def get_reports():
    """
    Lista todos os reports com suporte a paginação e filtros

    Query params:
    - page: número da página (padrão: 1)
    - per_page: itens por página (padrão: 50, max: 100)
    - status: filtrar por status (aberto, em_execucao, resolvido)
    - category: filtrar por categoria
    """
    try:
        # Parâmetros de paginação
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 100)

        # Construir query base
        query = Report.query

        # Filtros opcionais
        status = request.args.get('status')
        if status:
            query = query.filter_by(status=status)

        category = request.args.get('category')
        if category:
            query = query.filter_by(category=category)

        # Ordenar por mais recentes
        query = query.order_by(Report.created_at.desc())

        # Paginar
        pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )

        reports = pagination.items

        return jsonify({
            'success': True,
            'data': [report.to_dict() for report in reports],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            }
        }), 200

    except Exception as e:
        current_app.logger.error(f"Erro ao listar reports: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Erro interno ao buscar denúncias'
        }), 500

@api_bp.route('/reports', methods=['POST'])
def create_report():
    """Cria um novo report"""
    try:
        # Aceita tanto form-data quanto JSON
        payload = request.form.to_dict(flat=True) if request.form else (request.get_json(silent=True) or {})

        def get_value(field, default=None):
            value = payload.get(field, default)
            return value if value not in ('', None) else default

        def resolve_from_user(*attrs):
            """Obtém o primeiro atributo disponível do usuário autenticado."""
            if not current_user.is_authenticated:
                return None
            for attr in attrs:
                value = getattr(current_user, attr, None)
                if value not in (None, ''):
                    return value
            return None

        # Validar campos obrigatórios mínimos
        required_fields = ['title', 'description', 'category', 'lat', 'lng']
        errors = [f'Campo {field} é obrigatório' for field in required_fields if not get_value(field)]

        if errors:
            return jsonify({
                'success': False,
                'errors': errors
            }), 400

        # Validar coordenadas
        try:
            lat = float(get_value('lat'))
            lng = float(get_value('lng'))

            if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
                return jsonify({
                    'success': False,
                    'errors': ['Coordenadas inválidas']
                }), 400
        except (TypeError, ValueError):
            return jsonify({
                'success': False,
                'errors': ['Latitude e longitude devem ser números']
            }), 400

        # Processar upload de imagem
        image_path = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                # Validar arquivo
                validation = validate_image_file(file, max_size_mb=10)

                if not validation.get('valid'):
                    return jsonify({
                        'success': False,
                        'errors': [validation.get('message')]
                    }), 400

                # Gerar nome único
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                safe_filename = validation.get('safe_filename')
                filename = f"{timestamp}_{safe_filename}"

                upload_folder = current_app.config['UPLOAD_FOLDER']
                os.makedirs(upload_folder, exist_ok=True)

                filepath = os.path.join(upload_folder, filename)
                file.save(filepath)
                image_path = filename

        # Dados do município podem vir do payload ou do usuário autenticado
        municipio_ibge_id_raw = get_value('municipio_ibge_id') or resolve_from_user('municipio_ibge_id', 'municipio_origem_id')
        municipio_nome = get_value('municipio_nome') or resolve_from_user('municipio_nome', 'municipio_origem_nome')
        municipio_uf = get_value('municipio_uf') or resolve_from_user('municipio_uf', 'municipio_origem_uf')

        municipio_ibge_id = None
        if municipio_ibge_id_raw is not None:
            try:
                municipio_ibge_id = int(municipio_ibge_id_raw)
            except (TypeError, ValueError):
                return jsonify({
                    'success': False,
                    'errors': ['municipio_ibge_id inválido']
                }), 400

        # Buscar órgão responsável somente se houver município
        orgao = None
        if municipio_ibge_id:
            orgao = User.query.filter_by(
                user_type='orgao',
                municipio_ibge_id=municipio_ibge_id,
                is_active=True,
                is_approved=True
            ).first()

        # Criar report
        report = Report(
            title=get_value('title'),
            description=get_value('description'),
            category=get_value('category'),
            lat=lat,
            lng=lng,
            image_path=image_path,
            status='aberto',
            user_id=current_user.id if current_user.is_authenticated else None,
            municipio_ibge_id=municipio_ibge_id,
            municipio_nome=municipio_nome,
            municipio_uf=municipio_uf,
            assigned_to=orgao.id if orgao else None  # Atribuir automaticamente ao órgão
        )

        db.session.add(report)
        db.session.flush()  # Para obter o ID antes do commit

        # Criar entrada no histórico
        if current_user.is_authenticated:
            history_entry = ReportHistory(
                report_id=report.id,
                user_id=current_user.id,
                action='criado',
                new_status='aberto',
                comment=f'Chamado criado por {current_user.name}'
            )
            db.session.add(history_entry)

        db.session.commit()

        current_app.logger.info(f"Report criado: {report.id} - {report.title}")

        return jsonify({
            'success': True,
            'data': report.to_dict(),
            'message': 'Denúncia criada com sucesso'
        }), 201

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao criar report: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Erro interno ao criar denúncia'
        }), 500

@api_bp.route('/reports/<int:report_id>', methods=['GET'])
def get_report(report_id):
    """Busca um report específico por ID"""
    try:
        report = Report.query.get(report_id)

        if not report:
            return jsonify({
                'success': False,
                'error': 'Denúncia não encontrada'
            }), 404

        return jsonify({
            'success': True,
            'data': report.to_dict()
        }), 200

    except Exception as e:
        current_app.logger.error(f"Erro ao buscar report {report_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Erro interno ao buscar denúncia'
        }), 500

@api_bp.route('/reports/<int:report_id>', methods=['PATCH'])
@login_required
def update_report_status(report_id):
    """Atualiza o status de um report (apenas órgãos)"""
    try:
        # Apenas órgãos ou administradores podem atualizar status
        if not (current_user.is_agency or current_user.is_admin):
            return jsonify({
                'success': False,
                'error': 'Apenas órgãos competentes ou administradores podem atualizar chamados'
            }), 403

        report = Report.query.get(report_id)

        if not report:
            return jsonify({
                'success': False,
                'error': 'Denúncia não encontrada'
            }), 404

        data = request.get_json(silent=True) or {}
        new_status = data.get('status')
        comment = data.get('comment', '')

        # Validar status
        valid_statuses = {'aberto', 'visualizado', 'em_andamento', 'em_execucao', 'resolvido', 'rejeitado'}
        if new_status not in valid_statuses:
            return jsonify({
                'success': False,
                'error': f'Status inválido. Use: {", ".join(valid_statuses)}'
            }), 400

        status_aliases = {
            'em_execucao': 'em_andamento'
        }
        canonical_status = status_aliases.get(new_status, new_status)

        # Guardar status antigo
        old_status = report.status

        # Atualizar report
        report.status = canonical_status
        report.updated_at = datetime.utcnow()

        # Se está sendo atribuído pela primeira vez
        if not report.assigned_to:
            report.assigned_to = current_user.id

        # Adicionar ao histórico
        history_entry = ReportHistory(
            report_id=report.id,
            user_id=current_user.id,
            action='status_alterado',
            old_status=old_status,
            new_status=canonical_status,
            comment=comment or f'Status alterado de {old_status} para {new_status}'
        )
        db.session.add(history_entry)

        db.session.commit()

        current_app.logger.info(f"Report {report_id} atualizado para {new_status} por {current_user.name}")

        return jsonify({
            'success': True,
            'data': report.to_dict(),
            'message': 'Status atualizado com sucesso'
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao atualizar report {report_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Erro interno ao atualizar denúncia'
        }), 500

@api_bp.route('/reports/<int:report_id>', methods=['DELETE'])
@login_required
def delete_report(report_id):
    """Deleta um report (apenas admin)"""
    try:
        if not current_user.is_admin:
            return jsonify({
                'success': False,
                'error': 'Apenas administradores podem deletar denúncias'
            }), 403

        report = Report.query.get(report_id)

        if not report:
            return jsonify({
                'success': False,
                'error': 'Denúncia não encontrada'
            }), 404

        # Deletar imagem associada se existir
        if report.image_path:
            try:
                image_full_path = os.path.join(
                    current_app.config['UPLOAD_FOLDER'],
                    report.image_path
                )
                if os.path.exists(image_full_path):
                    os.remove(image_full_path)
            except Exception as img_error:
                current_app.logger.warning(f"Erro ao deletar imagem: {str(img_error)}")

        db.session.delete(report)
        db.session.commit()

        current_app.logger.info(f"Report {report_id} deletado")

        return jsonify({
            'success': True,
            'message': 'Denúncia deletada com sucesso'
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao deletar report {report_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Erro interno ao deletar denúncia'
        }), 500

@api_bp.route('/reports/<int:report_id>/history', methods=['GET'])
def get_report_history(report_id):
    """Retorna o histórico de um report"""
    try:
        report = Report.query.get(report_id)

        if not report:
            return jsonify({
                'success': False,
                'error': 'Denúncia não encontrada'
            }), 404

        history = ReportHistory.query.filter_by(report_id=report_id).order_by(ReportHistory.created_at.asc()).all()

        return jsonify({
            'success': True,
            'data': [entry.to_dict() for entry in history]
        }), 200

    except Exception as e:
        current_app.logger.error(f"Erro ao buscar histórico do report {report_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Erro interno ao buscar histórico'
        }), 500

@api_bp.route('/reports/<int:report_id>/comment', methods=['POST'])
@login_required
def add_comment(report_id):
    """Adiciona um comentário ao histórico do report (apenas órgãos)"""
    try:
        # Apenas órgãos podem comentar
        if not current_user.is_agency:
            return jsonify({
                'success': False,
                'error': 'Apenas órgãos competentes podem adicionar comentários'
            }), 403

        report = Report.query.get(report_id)

        if not report:
            return jsonify({
                'success': False,
                'error': 'Denúncia não encontrada'
            }), 404

        data = request.get_json()
        comment = data.get('comment', '').strip()

        if not comment:
            return jsonify({
                'success': False,
                'error': 'Comentário não pode ser vazio'
            }), 400

        # Adicionar comentário ao histórico
        history_entry = ReportHistory(
            report_id=report.id,
            user_id=current_user.id,
            action='comentario',
            comment=comment
        )
        db.session.add(history_entry)

        # Atualizar data de modificação do report
        report.updated_at = datetime.utcnow()

        db.session.commit()

        current_app.logger.info(f"Comentário adicionado ao report {report_id} por {current_user.name}")

        return jsonify({
            'success': True,
            'data': history_entry.to_dict(),
            'message': 'Comentário adicionado com sucesso'
        }), 201

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao adicionar comentário ao report {report_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Erro interno ao adicionar comentário'
        }), 500

@api_bp.route('/stats', methods=['GET'])
def get_stats():
    """Retorna estatísticas gerais do sistema"""
    try:
        total_reports = Report.query.count()
        abertos = Report.query.filter_by(status='aberto').count()
        visualizados = Report.query.filter_by(status='visualizado').count()
        em_andamento = Report.query.filter_by(status='em_andamento').count()
        resolvidos = Report.query.filter_by(status='resolvido').count()
        rejeitados = Report.query.filter_by(status='rejeitado').count()

        # Estatísticas por categoria
        categories = {}
        for category in ['Iluminação', 'Vias', 'Água e Esgoto', 'Limpeza', 'Outros']:
            categories[category] = Report.query.filter_by(category=category).count()

        return jsonify({
            'success': True,
            'data': {
                'total': total_reports,
                'by_status': {
                    'aberto': abertos,
                    'visualizado': visualizados,
                    'em_andamento': em_andamento,
                    'resolvido': resolvidos,
                    'rejeitado': rejeitados
                },
                'by_category': categories
            }
        }), 200

    except Exception as e:
        current_app.logger.error(f"Erro ao buscar estatísticas: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Erro interno ao buscar estatísticas'
        }), 500


# ========== ROTAS DE MUNICÍPIOS E GEOCODING ==========

@api_bp.route('/municipios', methods=['GET'])
def get_municipios():
    """
    Busca municípios brasileiros

    Query params:
    - q: termo de busca (opcional)
    - uf: filtrar por UF (opcional)
    """
    try:
        from app.services.ibge_service import search_municipios, get_all_municipios

        query = request.args.get('q', '').strip()
        uf = request.args.get('uf', None)

        if query:
            municipios = search_municipios(query, uf)
        elif uf:
            from app.services.ibge_service import IBGEService
            municipios = IBGEService.get_municipios_by_uf(uf)[:50]
        else:
            # Retornar apenas primeiros 50 se não houver busca
            municipios = get_all_municipios()[:50]

        return jsonify({
            'success': True,
            'data': municipios,
            'count': len(municipios)
        }), 200

    except Exception as e:
        current_app.logger.error(f"Erro ao buscar municípios: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Erro ao buscar municípios'
        }), 500


@api_bp.route('/municipios/com-orgaos', methods=['GET'])
def get_municipios_com_orgaos():
    """
    Lista apenas municípios que têm órgãos cadastrados

    Query params:
    - q: termo de busca (opcional)
    """
    try:
        # Buscar municípios únicos dos órgãos ativos
        orgaos = User.query.filter_by(
            user_type='orgao',
            is_active=True,
            is_approved=True
        ).all()

        municipios_ids = set([o.municipio_ibge_id for o in orgaos if o.municipio_ibge_id])

        if not municipios_ids:
            return jsonify({
                'success': True,
                'data': [],
                'count': 0,
                'message': 'Nenhum órgão cadastrado ainda'
            }), 200

        # Buscar dados completos dos municípios
        from app.services.ibge_service import get_municipio
        municipios = []
        for mid in municipios_ids:
            municipio = get_municipio(mid)
            if municipio:
                municipios.append(municipio)

        # Ordenar por nome
        municipios.sort(key=lambda x: x['nome'])

        # Filtrar por busca se fornecido
        query = request.args.get('q', '').strip().lower()
        if query:
            municipios = [m for m in municipios if query in m['nome'].lower()]

        return jsonify({
            'success': True,
            'data': municipios,
            'count': len(municipios)
        }), 200

    except Exception as e:
        current_app.logger.error(f"Erro ao buscar municípios com órgãos: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Erro ao buscar municípios'
        }), 500


@api_bp.route('/geocode', methods=['POST'])
def geocode():
    """
    Converte coordenadas (lat/lng) em município

    Body (JSON):
    {
        "lat": -23.5505,
        "lng": -46.6333
    }

    Returns:
    {
        "success": true,
        "data": {
            "municipio": "São Paulo",
            "uf": "SP",
            "municipio_ibge_id": 3550308,
            "municipio_completo": "São Paulo/SP"
        }
    }
    """
    try:
        data = request.get_json(force=True)

        current_app.logger.info(f"Geocode request received: {data}")

        if not data or 'lat' not in data or 'lng' not in data:
            error_msg = 'Campos lat e lng são obrigatórios'
            current_app.logger.error(f"Geocode validation failed: {error_msg}. Data received: {data}")
            return jsonify({
                'success': False,
                'error': error_msg
            }), 400

        try:
            lat = float(data['lat'])
            lng = float(data['lng'])
        except (ValueError, TypeError) as e:
            error_msg = 'Coordenadas inválidas. lat e lng devem ser números.'
            current_app.logger.error(f"Invalid coordinates: {e}. Data: {data}")
            return jsonify({
                'success': False,
                'error': error_msg
            }), 400

        from app.services.geocoding_service import get_city_from_location
        result = get_city_from_location(lat, lng)

        current_app.logger.info(f"Geocoding result for ({lat}, {lng}): {result}")

        if result and result.get('valid'):
            return jsonify({
                'success': True,
                'data': result
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Não foi possível determinar o município'),
                'data': result
            }), 400

    except Exception as e:
        current_app.logger.error(f"Erro ao fazer geocoding: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Erro ao processar coordenadas: {str(e)}'
        }), 500
