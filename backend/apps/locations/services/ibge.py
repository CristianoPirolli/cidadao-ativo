"""
Municípios brasileiros a partir da API de localidades do IBGE.

A lista é baixada uma vez, gravada em ``settings.DATA_DIR`` e mantida em
memória pelo processo, evitando reler o arquivo a cada consulta.
"""
import json
import logging
from pathlib import Path

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

API_URL = 'https://servicodados.ibge.gov.br/api/v1/localidades/municipios'
CACHE_FILENAME = 'municipios_cache.json'
MAX_RESULTS = 50

_municipios: list[dict] | None = None
_by_id: dict[int, dict] = {}


def _cache_file() -> Path:
    return Path(settings.DATA_DIR) / CACHE_FILENAME


def _parse_uf(item: dict) -> dict | None:
    """Extrai a UF do município (a API usa duas estruturas diferentes)."""
    try:
        if item.get('microrregiao'):
            return item['microrregiao']['mesorregiao']['UF']
        if item.get('regiao-imediata'):
            return item['regiao-imediata']['regiao-intermediaria']['UF']
    except (KeyError, TypeError):
        pass
    return None


def _download() -> list[dict]:
    response = requests.get(API_URL, timeout=30)
    response.raise_for_status()

    municipios = []
    for item in response.json():
        uf = _parse_uf(item)
        if not uf:
            logger.warning('Município sem UF ignorado: %s', item.get('nome'))
            continue
        municipios.append({
            'id': item['id'],
            'nome': item['nome'],
            'uf': uf['sigla'],
            'uf_nome': uf['nome'],
            'nome_completo': f"{item['nome']}/{uf['sigla']}",
        })
    municipios.sort(key=lambda m: m['nome'])
    return municipios


def _load() -> list[dict]:
    cache_file = _cache_file()
    if cache_file.exists():
        try:
            return json.loads(cache_file.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            logger.exception('Cache de municípios inválido, baixando novamente')

    try:
        municipios = _download()
    except requests.RequestException:
        logger.exception('Erro ao buscar municípios do IBGE')
        return []

    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(municipios, ensure_ascii=False), encoding='utf-8')
    return municipios


def get_all_municipios() -> list[dict]:
    """Todos os municípios, ordenados por nome. Falhas não ficam em cache."""
    global _municipios, _by_id
    if not _municipios:
        _municipios = _load()
        _by_id = {m['id']: m for m in _municipios}
    return _municipios


def get_municipio(municipio_id: int) -> dict | None:
    get_all_municipios()
    return _by_id.get(municipio_id)


def get_municipios_by_uf(uf: str) -> list[dict]:
    uf = uf.strip().upper()
    return [m for m in get_all_municipios() if m['uf'] == uf]


def search_municipios(query: str, uf: str | None = None) -> list[dict]:
    """Municípios cujo nome contém ``query`` (opcionalmente filtrados por UF)."""
    query = query.strip().lower()
    candidates = get_municipios_by_uf(uf) if uf else get_all_municipios()
    return [m for m in candidates if query in m['nome'].lower()][:MAX_RESULTS]


def find_municipio(nome: str, uf: str) -> dict | None:
    """Correspondência exata (sem diferenciar maiúsculas) de nome e UF."""
    nome = nome.strip().lower()
    return next((m for m in get_municipios_by_uf(uf) if m['nome'].lower() == nome), None)
