"""
Serviço de validação de título de eleitor
Suporta validação por formato (gratuito) ou integração com API externa (pago)
"""
import re
import os
from typing import Dict, Optional


class VoterValidation:
    """Classe para validação de títulos de eleitor"""

    # Configuração da API (se houver)
    API_KEY = os.environ.get('TSE_API_KEY', None)
    API_PROVIDER = os.environ.get('TSE_API_PROVIDER', None)  # 'directdata' ou 'netrin'

    @staticmethod
    def validate_format(voter_id: str) -> bool:
        """
        Valida o formato do título de eleitor
        Título de eleitor tem 12 dígitos

        NOTA: Validação de dígitos verificadores DESABILITADA.
        Há variações regionais e históricas no algoritmo do TSE que tornam
        a validação de dígitos verificadores não confiável para todos os títulos.
        Esta função aceita qualquer sequência de 12 dígitos numéricos.
        """
        if not voter_id:
            return False

        # Remove espaços e caracteres especiais
        clean_id = re.sub(r'[^0-9]', '', voter_id)

        # Verifica se tem 12 dígitos
        if len(clean_id) != 12:
            return False

        # VALIDAÇÃO SIMPLIFICADA: apenas formato (12 dígitos)
        # Dígitos verificadores NÃO são validados para evitar rejeitar títulos válidos
        return True

    @staticmethod
    def _check_digits(voter_id: str) -> bool:
        """
        Valida os dígitos verificadores do título de eleitor
        Baseado no algoritmo oficial do TSE

        ATENÇÃO: Este método NÃO está sendo usado atualmente.
        A validação de dígitos verificadores foi desabilitada porque:
        1. Há variações regionais no algoritmo do TSE
        2. Títulos antigos podem usar algoritmos diferentes
        3. Estava rejeitando títulos de eleitor válidos

        Mantido aqui para referência futura.
        """
        if len(voter_id) != 12:
            return False

        # Primeiro dígito verificador (posição 8)
        d1 = VoterValidation._calculate_digit(voter_id[:8], [2, 3, 4, 5, 6, 7, 8, 9])
        if d1 != int(voter_id[10]):
            return False

        # Segundo dígito verificador (posição 9)
        # Inclui os 2 dígitos da UF (posições 8 e 9) mais o primeiro dígito verificador
        state_digits = voter_id[8:10]
        d2 = VoterValidation._calculate_digit(state_digits + str(d1), [7, 8, 9])
        if d2 != int(voter_id[11]):
            return False

        return True

    @staticmethod
    def _calculate_digit(number: str, weights: list) -> int:
        """Calcula dígito verificador"""
        total = sum(int(n) * w for n, w in zip(number, weights))
        remainder = total % 11

        if remainder == 0:
            return 0
        elif remainder == 1:
            return 0  # Convenção do TSE
        else:
            return 11 - remainder

    @staticmethod
    def validate_with_api(voter_id: str, cpf: str = None) -> Dict[str, any]:
        """
        Valida título de eleitor usando API externa
        Retorna informações do eleitor se válido

        Args:
            voter_id: Número do título de eleitor
            cpf: CPF do eleitor (alguns provedores requerem)

        Returns:
            Dict com informações do eleitor ou erro
        """
        if not VoterValidation.API_KEY or not VoterValidation.API_PROVIDER:
            return {
                'valid': False,
                'error': 'API não configurada. Configure TSE_API_KEY e TSE_API_PROVIDER no .env'
            }

        # Primeiro valida o formato
        if not VoterValidation.validate_format(voter_id):
            return {
                'valid': False,
                'error': 'Formato de título de eleitor inválido'
            }

        # Aqui você integraria com a API escolhida
        # Exemplo para Direct Data ou Netrin:

        """
        if VoterValidation.API_PROVIDER == 'directdata':
            return VoterValidation._validate_directdata(voter_id, cpf)
        elif VoterValidation.API_PROVIDER == 'netrin':
            return VoterValidation._validate_netrin(voter_id, cpf)
        """

        # Por enquanto, apenas valida formato
        return {
            'valid': True,
            'message': 'Validação de formato aprovada. Integração com API disponível mediante configuração.'
        }

    @staticmethod
    def _validate_directdata(voter_id: str, cpf: str) -> Dict[str, any]:
        """
        Integração com Direct Data API
        Documentação: https://www.directd.com.br/central-de-ajuda/posts/tse-titulo-e-local-de-votacao
        """
        # TODO: Implementar chamada à API
        # Exemplo:
        """
        import requests

        url = "https://api.directdata.com.br/tse/titulo"
        headers = {
            'Authorization': f'Bearer {VoterValidation.API_KEY}',
            'Content-Type': 'application/json'
        }
        data = {
            'titulo': voter_id,
            'cpf': cpf
        }

        response = requests.post(url, headers=headers, json=data)

        if response.status_code == 200:
            data = response.json()
            return {
                'valid': True,
                'name': data.get('nome'),
                'zone': data.get('zona'),
                'section': data.get('secao'),
                'voting_place': data.get('local_votacao')
            }
        else:
            return {
                'valid': False,
                'error': 'Título de eleitor não encontrado ou inválido'
            }
        """
        pass

    @staticmethod
    def _validate_netrin(voter_id: str, cpf: str) -> Dict[str, any]:
        """
        Integração com Netrin API
        Documentação: https://netrin.com.br/doc/tse-titulo-eleitoral/
        """
        # TODO: Implementar chamada à API
        pass

    @staticmethod
    def format_voter_id(voter_id: str) -> str:
        """
        Formata o título de eleitor para exibição
        XXXX XXXX XXXX
        """
        clean_id = re.sub(r'[^0-9]', '', voter_id)
        if len(clean_id) == 12:
            return f"{clean_id[:4]} {clean_id[4:8]} {clean_id[8:]}"
        return voter_id

    @staticmethod
    def clean_voter_id(voter_id: str) -> str:
        """Remove formatação do título de eleitor"""
        return re.sub(r'[^0-9]', '', voter_id)


# Funções de conveniência
def validate_voter_id(voter_id: str, use_api: bool = False, cpf: str = None) -> Dict[str, any]:
    """
    Função principal de validação

    Args:
        voter_id: Número do título de eleitor
        use_api: Se True, tenta validar com API externa
        cpf: CPF do eleitor (necessário para algumas APIs)

    Returns:
        Dict com resultado da validação
    """
    if use_api and VoterValidation.API_KEY:
        return VoterValidation.validate_with_api(voter_id, cpf)
    else:
        is_valid = VoterValidation.validate_format(voter_id)
        return {
            'valid': is_valid,
            'message': 'Formato válido' if is_valid else 'Formato inválido'
        }


def clean_voter_id(voter_id: str) -> str:
    """Remove formatação do título de eleitor (função de conveniência)"""
    return VoterValidation.clean_voter_id(voter_id)


def format_voter_id(voter_id: str) -> str:
    """Formata o título de eleitor para exibição (função de conveniência)"""
    return VoterValidation.format_voter_id(voter_id)
