from unittest import mock

import pytest
import requests

from apps.core.services.cnpj import clean_cnpj, has_valid_digits, validate_cnpj


@pytest.mark.parametrize('cnpj, valid', [
    ('11.222.333/0001-81', True),
    ('11222333000181', True),
    ('11.222.333/0001-80', False),
    ('11111111111111', False),
    ('123', False),
])
def test_has_valid_digits(cnpj, valid):
    assert has_valid_digits(cnpj) is valid


def test_clean_cnpj():
    assert clean_cnpj('11.222.333/0001-81') == '11222333000181'


def test_validate_cnpj_without_api():
    assert validate_cnpj('11222333000181', use_api=False)['valid'] is True


def test_validate_cnpj_rejects_unknown_on_receitaws():
    response = mock.Mock(status_code=200, json=lambda: {'status': 'ERROR', 'message': 'CNPJ inválido'})
    with mock.patch('apps.core.services.cnpj.requests.get', return_value=response):
        assert validate_cnpj('11222333000181')['valid'] is False


def test_validate_cnpj_accepts_when_api_is_down():
    with mock.patch('apps.core.services.cnpj.requests.get', side_effect=requests.Timeout):
        assert validate_cnpj('11222333000181')['valid'] is True
