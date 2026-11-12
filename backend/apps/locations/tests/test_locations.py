import json
from unittest import mock

import pytest
from django.urls import reverse

from conftest import MUNICIPIO


@pytest.mark.django_db
def test_geocode_requires_coordinates(client):
    response = client.post(reverse('api_geocode'), data='{}', content_type='application/json')
    assert response.status_code == 400


@pytest.mark.django_db
def test_geocode_returns_city(client):
    fake = {'valid': True, 'municipio_ibge_id': MUNICIPIO['id'], 'municipio': MUNICIPIO['nome'], 'uf': 'SC'}
    with mock.patch('apps.locations.api.get_city_from_location', return_value=fake):
        response = client.post(
            reverse('api_geocode'), data=json.dumps({'lat': -27.5, 'lng': -48.5}), content_type='application/json'
        )
    assert response.status_code == 200
    assert response.json()['data']['municipio_ibge_id'] == MUNICIPIO['id']


@pytest.mark.django_db
def test_municipios_com_orgaos(client, agency):
    with mock.patch('apps.locations.api.get_municipio', return_value={'id': MUNICIPIO['id'], 'nome': MUNICIPIO['nome']}):
        response = client.get(reverse('api_municipios_com_orgaos'))
    assert response.json()['count'] == 1
