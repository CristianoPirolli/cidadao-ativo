"""
Serviço de validação de CNPJ
Valida CNPJ usando API da ReceitaWS (pública e gratuita)
"""
import re

import requests


def clean_cnpj(cnpj: str) -> str:
    """Remove formatação do CNPJ"""
    return re.sub(r'[^0-9]', '', cnpj)


def format_cnpj(cnpj: str) -> str:
    """Formata CNPJ para XX.XXX.XXX/XXXX-XX"""
    cnpj = clean_cnpj(cnpj)
    if len(cnpj) != 14:
        return cnpj
    return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:14]}"


def validate_cnpj_format(cnpj: str) -> bool:
    """Valida o formato do CNPJ (apenas estrutura, não dígitos verificadores)"""
    cnpj = clean_cnpj(cnpj)

    # Verifica se tem 14 dígitos
    if len(cnpj) != 14:
        return False

    # Verifica se não são todos iguais
    if cnpj == cnpj[0] * 14:
        return False

    return True


def calculate_cnpj_digit(cnpj: str, position: int) -> int:
    """Calcula o dígito verificador do CNPJ"""
    if position == 12:
        weights = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    else:  # position == 13
        weights = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]

    sum_value = sum(int(cnpj[i]) * weights[i] for i in range(len(weights)))
    remainder = sum_value % 11
    return 0 if remainder < 2 else 11 - remainder


def validate_cnpj_digits(cnpj: str) -> bool:
    """Valida os dígitos verificadores do CNPJ"""
    cnpj = clean_cnpj(cnpj)

    if not validate_cnpj_format(cnpj):
        return False

    # Verifica primeiro dígito
    digit1 = calculate_cnpj_digit(cnpj, 12)
    if digit1 != int(cnpj[12]):
        return False

    # Verifica segundo dígito
    digit2 = calculate_cnpj_digit(cnpj, 13)
    if digit2 != int(cnpj[13]):
        return False

    return True


def validate_cnpj_api(cnpj: str, use_api: bool = True) -> tuple[bool, dict]:
    """
    Valida CNPJ usando a API da ReceitaWS

    Args:
        cnpj: CNPJ a ser validado
        use_api: Se False, valida apenas formato e dígitos verificadores

    Returns:
        Tuple (is_valid, data)
    """
    cnpj_clean = clean_cnpj(cnpj)

    # Validação básica de formato
    if not validate_cnpj_format(cnpj_clean):
        return False, {
            "valid": False,
            "message": "CNPJ inválido: formato incorreto",
            "cnpj": format_cnpj(cnpj_clean)
        }

    # Validação de dígitos verificadores
    if not validate_cnpj_digits(cnpj_clean):
        return False, {
            "valid": False,
            "message": "CNPJ inválido: dígitos verificadores incorretos",
            "cnpj": format_cnpj(cnpj_clean)
        }

    # Se não deve usar API, retorna válido apenas com validação básica
    if not use_api:
        return True, {
            "valid": True,
            "message": "CNPJ válido (validação local)",
            "cnpj": format_cnpj(cnpj_clean)
        }

    # Consulta API da ReceitaWS
    try:
        url = f"https://www.receitaws.com.br/v1/cnpj/{cnpj_clean}"
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            data = response.json()

            # Verifica se o CNPJ está ativo
            if data.get("status") == "ERROR":
                return False, {
                    "valid": False,
                    "message": f"CNPJ não encontrado: {data.get('message', 'Erro desconhecido')}",
                    "cnpj": format_cnpj(cnpj_clean)
                }

            # CNPJ encontrado e válido
            return True, {
                "valid": True,
                "message": "CNPJ válido e ativo",
                "cnpj": format_cnpj(cnpj_clean),
                "nome": data.get("nome", ""),
                "fantasia": data.get("fantasia", ""),
                "situacao": data.get("situacao", ""),
                "municipio": data.get("municipio", ""),
                "uf": data.get("uf", ""),
                "atividade_principal": data.get("atividade_principal", [{}])[0].get("text", "") if data.get("atividade_principal") else ""
            }

        elif response.status_code == 429:
            # Rate limit - validar apenas localmente
            return True, {
                "valid": True,
                "message": "CNPJ válido (API temporariamente indisponível)",
                "cnpj": format_cnpj(cnpj_clean),
                "warning": "Validação completa via API não disponível no momento"
            }

        else:
            # Erro na API - validar apenas localmente
            return True, {
                "valid": True,
                "message": "CNPJ válido (erro ao consultar API)",
                "cnpj": format_cnpj(cnpj_clean),
                "warning": "Não foi possível verificar com a Receita Federal"
            }

    except requests.exceptions.Timeout:
        # Timeout - validar apenas localmente
        return True, {
            "valid": True,
            "message": "CNPJ válido (timeout na API)",
            "cnpj": format_cnpj(cnpj_clean),
            "warning": "Tempo de espera excedido na consulta à Receita Federal"
        }

    except Exception as e:
        # Erro genérico - validar apenas localmente
        return True, {
            "valid": True,
            "message": "CNPJ válido (erro ao consultar API)",
            "cnpj": format_cnpj(cnpj_clean),
            "warning": f"Erro ao consultar Receita Federal: {str(e)}"
        }


# Função principal para uso no registro
def validate_cnpj(cnpj: str, use_api: bool = True) -> dict:
    """
    Função principal de validação de CNPJ

    Args:
        cnpj: CNPJ a ser validado
        use_api: Se deve consultar API da Receita Federal

    Returns:
        Dict com resultado da validação
    """
    is_valid, data = validate_cnpj_api(cnpj, use_api=use_api)
    return data
