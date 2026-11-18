"""
Validação de CNPJ: dígitos verificadores e, opcionalmente, consulta à ReceitaWS.

Se a API estiver indisponível, o CNPJ é aceito com base apenas na validação local.
"""
import logging
import re

import requests

logger = logging.getLogger(__name__)

RECEITAWS_URL = 'https://www.receitaws.com.br/v1/cnpj/{cnpj}'
WEIGHTS_1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
WEIGHTS_2 = [6, *WEIGHTS_1]


def clean_cnpj(cnpj: str) -> str:
    """Remove a formatação, mantendo apenas os dígitos."""
    return re.sub(r'\D', '', cnpj or '')


def _check_digit(digits: str, weights: list[int]) -> int:
    remainder = sum(int(d) * w for d, w in zip(digits, weights, strict=False)) % 11
    return 0 if remainder < 2 else 11 - remainder


def has_valid_digits(cnpj: str) -> bool:
    cnpj = clean_cnpj(cnpj)
    if len(cnpj) != 14 or cnpj == cnpj[0] * 14:
        return False
    return _check_digit(cnpj, WEIGHTS_1) == int(cnpj[12]) and _check_digit(cnpj, WEIGHTS_2) == int(cnpj[13])


def validate_cnpj(cnpj: str, use_api: bool = True) -> dict:
    """Retorna ``{'valid': bool, 'message': str}``."""
    cnpj = clean_cnpj(cnpj)
    if not has_valid_digits(cnpj):
        return {'valid': False, 'message': 'CNPJ inválido: formato ou dígitos verificadores incorretos'}
    if not use_api:
        return {'valid': True, 'message': 'CNPJ válido (validação local)'}

    try:
        response = requests.get(RECEITAWS_URL.format(cnpj=cnpj), timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'ERROR':
                return {'valid': False, 'message': f"CNPJ não encontrado: {data.get('message', 'erro desconhecido')}"}
            return {'valid': True, 'message': 'CNPJ válido e ativo'}
        logger.warning('ReceitaWS respondeu %s ao validar CNPJ', response.status_code)
    except (requests.RequestException, ValueError):
        logger.warning('Falha ao consultar a ReceitaWS', exc_info=True)
    return {'valid': True, 'message': 'CNPJ válido (Receita Federal indisponível no momento)'}
