from unittest import mock

import pytest

from apps.locations.services import geocoding, ibge

MUNICIPIOS = [
    {'id': 4205407, 'nome': 'Florianópolis', 'uf': 'SC', 'uf_nome': 'Santa Catarina',
     'nome_completo': 'Florianópolis/SC'},
    {'id': 4202404, 'nome': 'Blumenau', 'uf': 'SC', 'uf_nome': 'Santa Catarina', 'nome_completo': 'Blumenau/SC'},
    {'id': 3550308, 'nome': 'São Paulo', 'uf': 'SP', 'uf_nome': 'São Paulo', 'nome_completo': 'São Paulo/SP'},
]


@pytest.fixture
def municipios():
    """Base de municípios em memória, sem acessar a API do IBGE."""
    with mock.patch.object(ibge, '_load', return_value=MUNICIPIOS) as load:
        ibge._municipios = None
        yield load
    ibge._municipios = None


def test_municipios_are_loaded_once(municipios):
    assert ibge.get_municipio(4205407)['nome'] == 'Florianópolis'
    assert ibge.find_municipio('blumenau', 'sc')['id'] == 4202404
    assert [m['id'] for m in ibge.search_municipios('paulo')] == [3550308]
    assert municipios.call_count == 1


def test_failed_download_is_not_cached():
    with mock.patch.object(ibge, '_load', side_effect=[[], MUNICIPIOS]):
        ibge._municipios = None
        assert ibge.get_all_municipios() == []
        assert len(ibge.get_all_municipios()) == 3
    ibge._municipios = None


@pytest.mark.parametrize('name, expected', [
    ('Florianopolis', 4205407),         # sem acento
    ('Município de Blumenau', 4202404),  # palavras em comum
    ('Joinville', None),
])
def test_fuzzy_search(municipios, name, expected):
    result = geocoding.fuzzy_search_municipio(name, 'SC')
    assert (result or {}).get('id') == expected


def test_get_city_from_location(municipios):
    address = {'address': {'municipality': 'Região Geográfica Imediata', 'city': 'Florianopolis',
                           'state': 'Santa Catarina'}}
    with mock.patch.object(geocoding, 'reverse_geocode', return_value=address):
        result = geocoding.get_city_from_location(-27.59, -48.54)
    assert result == {
        'valid': True, 'municipio': 'Florianópolis', 'uf': 'SC',
        'municipio_ibge_id': 4205407, 'municipio_completo': 'Florianópolis/SC',
    }


def test_get_city_outside_brazil():
    assert geocoding.get_city_from_location(48.85, 2.35)['valid'] is False


def test_get_city_unknown_municipio(municipios):
    address = {'address': {'town': 'Cidade Inexistente', 'state': 'Santa Catarina'}}
    with mock.patch.object(geocoding, 'reverse_geocode', return_value=address):
        result = geocoding.get_city_from_location(-27.0, -49.0)
    assert result['valid'] is False
    assert result['municipio_completo'] == 'Cidade Inexistente/SC'


@pytest.fixture
def clear_cache():
    from django.core.cache import cache
    cache.clear()
    yield
    cache.clear()


def test_geocoding_result_is_cached(municipios, clear_cache):
    address = {'address': {'city': 'Florianópolis', 'state': 'Santa Catarina'}}
    with mock.patch.object(geocoding, 'reverse_geocode', return_value=address) as nominatim:
        first = geocoding.get_city_from_location(-27.59541, -48.54801)
        # Ponto a poucos metros: mesma célula do cache, sem nova consulta
        second = geocoding.get_city_from_location(-27.59543, -48.54799)
    assert first == second and first['valid']
    assert nominatim.call_count == 1


def test_failed_geocoding_is_not_cached(municipios, clear_cache):
    with mock.patch.object(geocoding, 'reverse_geocode', return_value=None) as nominatim:
        geocoding.get_city_from_location(-27.0, -49.0)
        geocoding.get_city_from_location(-27.0, -49.0)
    assert nominatim.call_count == 2


def test_nominatim_slot_is_shared(monkeypatch, clear_cache):
    from django.core.cache import cache
    sleeps = []
    monkeypatch.setattr(geocoding.time, 'sleep', lambda seconds: (sleeps.append(seconds), cache.delete(geocoding.RATE_LIMIT_KEY)))
    geocoding._wait_for_rate_limit()          # pega a vaga livre
    assert sleeps == []
    geocoding._wait_for_rate_limit()          # vaga ocupada (outro processo): espera
    assert sleeps
