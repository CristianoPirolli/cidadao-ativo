"""API de localidades: municípios (IBGE) e geocodificação reversa."""
import json
import logging

from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from apps.accounts.models import User, UserType
from apps.locations.services.geocoding import get_city_from_location
from apps.locations.services.ibge import IBGEService, get_all_municipios, get_municipio, search_municipios

logger = logging.getLogger(__name__)


@require_GET
def get_municipios(request):
    try:
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
        logger.exception(f'Erro ao buscar municípios: {e}')
        return JsonResponse({'success': False, 'error': 'Erro ao buscar municípios'}, status=500)


@require_GET
def get_municipios_com_orgaos(request):
    try:
        orgaos = User.objects.filter(user_type=UserType.AGENCY, is_active=True, is_approved=True).values_list('municipio_ibge_id', flat=True)
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
        logger.exception(f'Erro ao buscar municípios com órgãos: {e}')
        return JsonResponse({'success': False, 'error': 'Erro ao buscar municípios'}, status=500)


@require_POST
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

        result = get_city_from_location(lat, lng)

        if result and result.get('valid'):
            return JsonResponse({'success': True, 'data': result})
        return JsonResponse({'success': False, 'error': result.get('error', 'Não foi possível determinar o município'), 'data': result}, status=400)

    except Exception as e:
        logger.exception(f'Erro ao fazer geocoding: {e}')
        return JsonResponse({'success': False, 'error': 'Erro ao processar coordenadas'}, status=500)
