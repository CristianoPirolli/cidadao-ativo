"""
Geocodificação reversa: coordenadas → município do IBGE.

Usa o Nominatim (OpenStreetMap) para obter o endereço e cruza o nome da
cidade com a base de municípios do IBGE (correspondência exata e aproximada).
"""
import logging
import re
import threading
import time
import unicodedata

import requests
from django.core.cache import cache

from apps.locations.services.ibge import find_municipio, get_municipios_by_uf

logger = logging.getLogger(__name__)

NOMINATIM_URL = 'https://nominatim.openstreetmap.org/reverse'
# O Nominatim exige um User-Agent que identifique a aplicação
USER_AGENT = 'CidadaoAtivo/1.0 (contato@cidadaoativo.com)'

# Campos do endereço onde o Nominatim pode devolver o nome da cidade, por prioridade
CITY_FIELDS = ('city', 'town', 'village', 'municipality', 'county')
STOPWORDS = {'de', 'do', 'da', 'dos', 'das'}

# Resultados encontrados ficam em cache: 4 casas decimais ≈ 11 m
CACHE_TIMEOUT = 30 * 24 * 60 * 60
CACHE_PRECISION = 4
# Política de uso do Nominatim: no máximo 1 requisição por segundo
MIN_INTERVAL_SECONDS = 1.0
_rate_lock = threading.Lock()
_last_request_at = 0.0

STATE_TO_UF = {
    'acre': 'AC', 'alagoas': 'AL', 'amapá': 'AP', 'amazonas': 'AM', 'bahia': 'BA',
    'ceará': 'CE', 'distrito federal': 'DF', 'espírito santo': 'ES', 'goiás': 'GO',
    'maranhão': 'MA', 'mato grosso': 'MT', 'mato grosso do sul': 'MS', 'minas gerais': 'MG',
    'pará': 'PA', 'paraíba': 'PB', 'paraná': 'PR', 'pernambuco': 'PE', 'piauí': 'PI',
    'rio de janeiro': 'RJ', 'rio grande do norte': 'RN', 'rio grande do sul': 'RS',
    'rondônia': 'RO', 'roraima': 'RR', 'santa catarina': 'SC', 'são paulo': 'SP',
    'sergipe': 'SE', 'tocantins': 'TO',
}


def is_in_brazil(lat: float, lng: float) -> bool:
    """Verificação aproximada (retângulo que envolve o território brasileiro)."""
    return -35 <= lat <= 6 and -75 <= lng <= -30


def normalize_text(text: str) -> str:
    """Minúsculas, sem acentos nem pontuação e com espaços simples."""
    text = unicodedata.normalize('NFKD', (text or '').lower()).encode('ASCII', 'ignore').decode('ASCII')
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9\s]', '', text)).strip()


def _wait_for_rate_limit():
    global _last_request_at
    with _rate_lock:
        wait = MIN_INTERVAL_SECONDS - (time.monotonic() - _last_request_at)
        if wait > 0:
            time.sleep(wait)
        _last_request_at = time.monotonic()


def reverse_geocode(lat: float, lng: float) -> dict | None:
    """Endereço do Nominatim para as coordenadas, ou ``None`` em caso de falha."""
    _wait_for_rate_limit()
    try:
        response = requests.get(
            NOMINATIM_URL,
            params={'lat': lat, 'lon': lng, 'format': 'json', 'addressdetails': 1, 'accept-language': 'pt-BR,pt'},
            headers={'User-Agent': USER_AGENT},
            timeout=10,
        )
    except requests.RequestException:
        logger.exception('Erro ao consultar o Nominatim')
        return None
    if response.status_code != 200:
        logger.warning('Nominatim respondeu %s', response.status_code)
        return None
    return response.json()


def _extract_city(address: dict) -> str | None:
    for field in CITY_FIELDS:
        value = address.get(field)
        # "municipality" às vezes traz a região geográfica em vez do município
        if value and 'região geográfica' not in value.lower():
            return value
    return address.get('city_district')


def fuzzy_search_municipio(name: str, uf: str) -> dict | None:
    """Correspondência aproximada: nome normalizado, prefixo e palavras em comum."""
    if not name or not uf:
        return None
    candidates = [(m, normalize_text(m['nome'])) for m in get_municipios_by_uf(uf)]
    target = normalize_text(name)

    for municipio, normalized in candidates:
        if normalized == target:
            return municipio
    for municipio, normalized in candidates:
        if normalized.startswith(target) or target.startswith(normalized):
            return municipio

    target_words = set(target.split()) - STOPWORDS
    best, best_score = None, 0.0
    for municipio, normalized in candidates:
        words = set(normalized.split())
        common = target_words & words
        if common:
            score = len(common) / max(len(target_words), len(words))
            if score > best_score:
                best, best_score = municipio, score
    return best if best_score >= 0.5 else None


def get_city_from_location(lat: float, lng: float) -> dict:
    """Município do IBGE para as coordenadas, usando o cache quando possível."""
    key = f'geocode:{round(lat, CACHE_PRECISION)}:{round(lng, CACHE_PRECISION)}'
    cached = cache.get(key)
    if cached is not None:
        return cached
    result = _lookup_city(lat, lng)
    if result.get('valid'):
        cache.set(key, result, CACHE_TIMEOUT)
    return result


def _lookup_city(lat: float, lng: float) -> dict:
    """
    Município do IBGE para as coordenadas.

    Retorna ``{'valid': True, 'municipio', 'uf', 'municipio_ibge_id', 'municipio_completo'}``
    ou ``{'valid': False, 'error', ...}`` com os dados parciais encontrados.
    """
    if not is_in_brazil(lat, lng):
        return {'valid': False, 'error': 'Coordenadas fora do Brasil. Verifique se a localização está correta.'}

    data = reverse_geocode(lat, lng)
    address = (data or {}).get('address') or {}
    city = _extract_city(address)
    state = address.get('state')
    if not city or not state:
        return {
            'valid': False,
            'error': 'Não foi possível determinar o município. '
                     'O serviço de localização pode estar temporariamente indisponível.',
        }

    uf = STATE_TO_UF.get(state.strip().lower())
    municipio = (find_municipio(city, uf) or fuzzy_search_municipio(city, uf)) if uf else None
    if municipio:
        return {
            'valid': True,
            'municipio': municipio['nome'],
            'uf': municipio['uf'],
            'municipio_ibge_id': municipio['id'],
            'municipio_completo': municipio['nome_completo'],
        }

    logger.info('Município não encontrado no IBGE: %s/%s', city, uf or state)
    return {
        'valid': False,
        'error': (
            f'Localização detectada: {city}/{uf or state}\n\n'
            'Este município não foi encontrado na base do IBGE ou pode estar com nome diferente. '
            'Por favor, selecione manualmente da lista abaixo.'
        ),
        'municipio': city,
        'uf': uf,
        'municipio_completo': f'{city}/{uf or state}',
    }
