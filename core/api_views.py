"""
API Views Django — equivalente ao api_routes.py do Flask
"""
import json
import logging
import math
import os
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.utils import timezone
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from core.models import Report, ReportHistory, ReportUrgencyVote, User
from app.services.file_validation import validate_image_file

logger = logging.getLogger(__name__)


def _distance_meters(lat1, lng1, lat2, lng2):
    earth_radius_m = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return earth_radius_m * c


def _order_by_priority(queryset):
    """Ordena por votos de urgência (desc) e data (desc)."""
    return queryset.annotate(
        vote_count=Count('urgency_votes', distinct=True)
    ).order_by('-vote_count', '-created_at')


def get_reports(request):
    try:
        page = int(request.GET.get('page', 1))
        per_page = min(int(request.GET.get('per_page', 50)), 100)

        qs = Report.objects.select_related('user', 'assigned_user')

        status = request.GET.get('status')
        if status:
            qs = qs.filter(status=status)

        category = request.GET.get('category')
        if category:
            qs = qs.filter(category=category)

        qs = _order_by_priority(qs)
        paginator = Paginator(qs, per_page)
        page_obj = paginator.get_page(page)

        return JsonResponse({
            'success': True,
            'data': [r.to_dict() for r in page_obj],
            'pagination': {
                'page': page_obj.number,
                'per_page': per_page,
                'total': paginator.count,
                'pages': paginator.num_pages,
                'has_next': page_obj.has_next(),
                'has_prev': page_obj.has_previous(),
            },
        })
    except Exception as e:
        logger.error(f'Erro ao listar reports: {e}')
        return JsonResponse({'success': False, 'error': 'Erro interno ao buscar denúncias'}, status=500)


@login_required
def vote_report_urgency(request, report_id):
    try:
        if not request.user.is_citizen:
            return JsonResponse({'success': False, 'error': 'Somente cidadãos podem votar urgência em chamados.'}, status=403)

        report = Report.objects.filter(pk=report_id).first()
        if not report:
            return JsonResponse({'success': False, 'error': 'Denúncia não encontrada'}, status=404)

        if report.user_id == request.user.id:
            return JsonResponse({'success': False, 'error': 'Você não pode votar urgência no seu próprio chamado.'}, status=400)

        if request.user.municipio_origem_id and report.municipio_ibge_id:
            if request.user.municipio_origem_id != report.municipio_ibge_id:
                return JsonResponse({'success': False, 'error': 'Você só pode votar em chamados do seu município.'}, status=403)

        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            data = {}

        lat = data.get('lat')
        lng = data.get('lng')
        if lat is None or lng is None:
            return JsonResponse({'success': False, 'error': 'Para votar, informe sua localização atual (lat/lng).'}, status=400)

        try:
            user_lat = float(lat)
            user_lng = float(lng)
        except (TypeError, ValueError):
            return JsonResponse({'success': False, 'error': 'Coordenadas inválidas para votação.'}, status=400)

        max_distance_m = settings.URGENCY_VOTE_MAX_DISTANCE_METERS
        distance_m = _distance_meters(user_lat, user_lng, report.lat, report.lng)
        if distance_m > max_distance_m:
            return JsonResponse({
                'success': False,
                'error': f'Votação permitida apenas no mesmo local do chamado (até {max_distance_m}m).',
                'distance_m': round(distance_m, 1),
            }, status=403)

        if ReportUrgencyVote.objects.filter(report=report, user=request.user).exists():
            return JsonResponse({
                'success': False,
                'error': 'Você já votou neste chamado.',
                'urgency_votes_count': report.urgency_votes_count,
            }, status=409)

        ReportUrgencyVote.objects.create(report=report, user=request.user)
        ReportHistory.objects.create(
            report=report,
            user=request.user,
            action='voto_urgencia',
            comment='Chamado recebeu um voto de urgência',
        )

        report.refresh_from_db()
        return JsonResponse({
            'success': True,
            'message': 'Voto de urgência registrado com sucesso.',
            'urgency_votes_count': report.urgency_votes_count,
        }, status=201)

    except Exception as e:
        logger.error(f'Erro ao votar urgência no report {report_id}: {e}')
        return JsonResponse({'success': False, 'error': 'Erro interno ao registrar voto de urgência'}, status=500)


@csrf_exempt
def create_report(request):
    try:
        payload = request.POST.dict() if request.POST else {}
        if not payload and request.body:
            try:
                payload = json.loads(request.body)
            except (json.JSONDecodeError, ValueError):
                payload = {}

        def get_value(field, default=None):
            value = payload.get(field, default)
            return value if value not in ('', None) else default

        def resolve_from_user(*attrs):
            if not request.user.is_authenticated:
                return None
            for attr in attrs:
                value = getattr(request.user, attr, None)
                if value not in (None, ''):
                    return value
            return None

        required_fields = ['title', 'description', 'category', 'lat', 'lng']
        errors = [f'Campo {f} é obrigatório' for f in required_fields if not get_value(f)]
        if errors:
            return JsonResponse({'success': False, 'errors': errors}, status=400)

        try:
            lat = float(get_value('lat'))
            lng = float(get_value('lng'))
            if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
                return JsonResponse({'success': False, 'errors': ['Coordenadas inválidas']}, status=400)
        except (TypeError, ValueError):
            return JsonResponse({'success': False, 'errors': ['Latitude e longitude devem ser números']}, status=400)

        image_path = None
        if 'image' in request.FILES:
            file = request.FILES['image']
            if file and file.name:
                validation = validate_image_file(file, max_size_mb=10)
                if not validation.get('valid'):
                    return JsonResponse({'success': False, 'errors': [validation.get('message')]}, status=400)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                safe_filename = validation.get('safe_filename')
                filename = f'{timestamp}_{safe_filename}'
                upload_folder = settings.MEDIA_ROOT
                os.makedirs(upload_folder, exist_ok=True)
                filepath = os.path.join(upload_folder, filename)
                with open(filepath, 'wb') as f:
                    for chunk in file.chunks():
                        f.write(chunk)
                image_path = filename

        municipio_ibge_id_raw = get_value('municipio_ibge_id') or resolve_from_user('municipio_ibge_id', 'municipio_origem_id')
        municipio_nome = get_value('municipio_nome') or resolve_from_user('municipio_nome', 'municipio_origem_nome')
        municipio_uf = get_value('municipio_uf') or resolve_from_user('municipio_uf', 'municipio_origem_uf')

        municipio_ibge_id = None
        if municipio_ibge_id_raw is not None:
            try:
                municipio_ibge_id = int(municipio_ibge_id_raw)
            except (TypeError, ValueError):
                return JsonResponse({'success': False, 'errors': ['municipio_ibge_id inválido']}, status=400)

        orgao = None
        if municipio_ibge_id:
            orgao = User.objects.filter(
                user_type='orgao',
                municipio_ibge_id=municipio_ibge_id,
                is_active=True,
                is_approved=True,
            ).first()

        report = Report.objects.create(
            title=get_value('title'),
            description=get_value('description'),
            category=get_value('category'),
            lat=lat,
            lng=lng,
            image_path=image_path,
            status='aberto',
            user=request.user if request.user.is_authenticated else None,
            municipio_ibge_id=municipio_ibge_id,
            municipio_nome=municipio_nome,
            municipio_uf=municipio_uf,
            assigned_user=orgao,
        )

        if request.user.is_authenticated:
            ReportHistory.objects.create(
                report=report,
                user=request.user,
                action='criado',
                new_status='aberto',
                comment=f'Chamado criado por {request.user.name}',
            )

        logger.info(f'Report criado: {report.id} - {report.title}')
        return JsonResponse({'success': True, 'data': report.to_dict(), 'message': 'Denúncia criada com sucesso'}, status=201)

    except Exception as e:
        logger.error(f'Erro ao criar report: {e}')
        return JsonResponse({'success': False, 'error': 'Erro interno ao criar denúncia'}, status=500)


def get_report(request, report_id):
    try:
        report = Report.objects.select_related('user', 'assigned_user').filter(pk=report_id).first()
        if not report:
            return JsonResponse({'success': False, 'error': 'Denúncia não encontrada'}, status=404)
        return JsonResponse({'success': True, 'data': report.to_dict()})
    except Exception as e:
        logger.error(f'Erro ao buscar report {report_id}: {e}')
        return JsonResponse({'success': False, 'error': 'Erro interno ao buscar denúncia'}, status=500)


@login_required
def update_report_status(request, report_id):
    try:
        if not (request.user.is_agency or request.user.is_admin):
            return JsonResponse({'success': False, 'error': 'Apenas órgãos ou administradores podem atualizar chamados'}, status=403)

        report = Report.objects.filter(pk=report_id).first()
        if not report:
            return JsonResponse({'success': False, 'error': 'Denúncia não encontrada'}, status=404)

        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            data = {}

        new_status = data.get('status')
        comment = data.get('comment', '')

        valid_statuses = {'aberto', 'visualizado', 'em_andamento', 'em_execucao', 'resolvido', 'rejeitado'}
        if new_status not in valid_statuses:
            return JsonResponse({'success': False, 'error': f'Status inválido. Use: {", ".join(valid_statuses)}'}, status=400)

        canonical_status = {'em_execucao': 'em_andamento'}.get(new_status, new_status)
        old_status = report.status
        report.status = canonical_status
        if not report.assigned_user_id:
            report.assigned_user = request.user
        report.save()

        ReportHistory.objects.create(
            report=report,
            user=request.user,
            action='status_alterado',
            old_status=old_status,
            new_status=canonical_status,
            comment=comment or f'Status alterado de {old_status} para {new_status}',
        )

        return JsonResponse({'success': True, 'data': report.to_dict(), 'message': 'Status atualizado com sucesso'})

    except Exception as e:
        logger.error(f'Erro ao atualizar report {report_id}: {e}')
        return JsonResponse({'success': False, 'error': 'Erro interno ao atualizar denúncia'}, status=500)


@login_required
def delete_report(request, report_id):
    try:
        if not request.user.is_admin:
            return JsonResponse({'success': False, 'error': 'Apenas administradores podem deletar denúncias'}, status=403)

        report = Report.objects.filter(pk=report_id).first()
        if not report:
            return JsonResponse({'success': False, 'error': 'Denúncia não encontrada'}, status=404)

        if report.image_path:
            try:
                full_path = os.path.join(settings.MEDIA_ROOT, report.image_path)
                if os.path.exists(full_path):
                    os.remove(full_path)
            except Exception as img_err:
                logger.warning(f'Erro ao deletar imagem: {img_err}')

        report.delete()
        return JsonResponse({'success': True, 'message': 'Denúncia deletada com sucesso'})

    except Exception as e:
        logger.error(f'Erro ao deletar report {report_id}: {e}')
        return JsonResponse({'success': False, 'error': 'Erro interno ao deletar denúncia'}, status=500)


def get_report_history(request, report_id):
    try:
        report = Report.objects.filter(pk=report_id).first()
        if not report:
            return JsonResponse({'success': False, 'error': 'Denúncia não encontrada'}, status=404)
        history = ReportHistory.objects.filter(report=report).select_related('user').order_by('created_at')
        return JsonResponse({'success': True, 'data': [h.to_dict() for h in history]})
    except Exception as e:
        logger.error(f'Erro ao buscar histórico do report {report_id}: {e}')
        return JsonResponse({'success': False, 'error': 'Erro interno ao buscar histórico'}, status=500)


@login_required
def add_comment(request, report_id):
    try:
        if not request.user.is_agency:
            return JsonResponse({'success': False, 'error': 'Apenas órgãos competentes podem adicionar comentários'}, status=403)

        report = Report.objects.filter(pk=report_id).first()
        if not report:
            return JsonResponse({'success': False, 'error': 'Denúncia não encontrada'}, status=404)

        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            data = {}

        comment = (data.get('comment') or '').strip()
        if not comment:
            return JsonResponse({'success': False, 'error': 'Comentário não pode ser vazio'}, status=400)

        history_entry = ReportHistory.objects.create(
            report=report,
            user=request.user,
            action='comentario',
            comment=comment,
        )
        report.save(update_fields=['updated_at'])

        return JsonResponse({'success': True, 'data': history_entry.to_dict(), 'message': 'Comentário adicionado com sucesso'}, status=201)

    except Exception as e:
        logger.error(f'Erro ao adicionar comentário ao report {report_id}: {e}')
        return JsonResponse({'success': False, 'error': 'Erro interno ao adicionar comentário'}, status=500)


def get_stats(request):
    try:
        stats = Report.objects.aggregate(
            total=Count('id'),
            abertos=Count('id', filter=Q(status='aberto')),
            visualizados=Count('id', filter=Q(status='visualizado')),
            em_andamento=Count('id', filter=Q(status='em_andamento')),
            resolvidos=Count('id', filter=Q(status='resolvido')),
            rejeitados=Count('id', filter=Q(status='rejeitado')),
        )
        categories = {}
        for cat in ['iluminacao', 'vias', 'agua_esgoto', 'limpeza', 'outros']:
            categories[cat] = Report.objects.filter(category=cat).count()

        return JsonResponse({
            'success': True,
            'data': {
                'total': stats['total'] or 0,
                'by_status': {
                    'aberto': stats['abertos'] or 0,
                    'visualizado': stats['visualizados'] or 0,
                    'em_andamento': stats['em_andamento'] or 0,
                    'resolvido': stats['resolvidos'] or 0,
                    'rejeitado': stats['rejeitados'] or 0,
                },
                'by_category': categories,
            },
        })
    except Exception as e:
        logger.error(f'Erro ao buscar estatísticas: {e}')
        return JsonResponse({'success': False, 'error': 'Erro interno ao buscar estatísticas'}, status=500)


def get_municipios(request):
    try:
        from app.services.ibge_service import search_municipios, get_all_municipios, IBGEService
        query = request.GET.get('q', '').strip()
        uf = request.GET.get('uf') or None
        if query:
            municipios = search_municipios(query, uf)
        elif uf:
            municipios = IBGEService.get_municipios_by_uf(uf)[:50]
        else:
            municipios = get_all_municipios()[:50]
        return JsonResponse({'success': True, 'data': municipios, 'count': len(municipios)})
    except Exception as e:
        logger.error(f'Erro ao buscar municípios: {e}')
        return JsonResponse({'success': False, 'error': 'Erro ao buscar municípios'}, status=500)


def get_municipios_com_orgaos(request):
    try:
        from app.services.ibge_service import get_municipio
        orgaos = User.objects.filter(user_type='orgao', is_active=True, is_approved=True).values_list('municipio_ibge_id', flat=True)
        municipios_ids = set(mid for mid in orgaos if mid)
        if not municipios_ids:
            return JsonResponse({'success': True, 'data': [], 'count': 0, 'message': 'Nenhum órgão cadastrado ainda'})

        municipios = [m for mid in municipios_ids if (m := get_municipio(mid))]
        municipios.sort(key=lambda x: x['nome'])

        query = request.GET.get('q', '').strip().lower()
        if query:
            municipios = [m for m in municipios if query in m['nome'].lower()]

        return JsonResponse({'success': True, 'data': municipios, 'count': len(municipios)})
    except Exception as e:
        logger.error(f'Erro ao buscar municípios com órgãos: {e}')
        return JsonResponse({'success': False, 'error': 'Erro ao buscar municípios'}, status=500)


@csrf_exempt
def geocode(request):
    try:
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            data = {}

        if not data or 'lat' not in data or 'lng' not in data:
            return JsonResponse({'success': False, 'error': 'Campos lat e lng são obrigatórios'}, status=400)

        try:
            lat = float(data['lat'])
            lng = float(data['lng'])
        except (ValueError, TypeError):
            return JsonResponse({'success': False, 'error': 'Coordenadas inválidas. lat e lng devem ser números.'}, status=400)

        from app.services.geocoding_service import get_city_from_location
        result = get_city_from_location(lat, lng)

        if result and result.get('valid'):
            return JsonResponse({'success': True, 'data': result})
        return JsonResponse({'success': False, 'error': result.get('error', 'Não foi possível determinar o município'), 'data': result}, status=400)

    except Exception as e:
        logger.error(f'Erro ao fazer geocoding: {e}', exc_info=True)
        return JsonResponse({'success': False, 'error': f'Erro ao processar coordenadas: {e}'}, status=500)
