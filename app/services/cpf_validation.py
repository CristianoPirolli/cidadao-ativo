"""
Serviço de validação de CPF
"""
import re


def clean_cpf(cpf: str) -> str:
    """
    Remove formatação do CPF (pontos, traços)

    Args:
        cpf: CPF com ou sem formatação

    Returns:
        CPF apenas com números
    """
    if not cpf:
        return ""
    return re.sub(r'\D', '', cpf)


def validate_cpf(cpf: str) -> dict:
    """
    Valida CPF brasileiro

    Args:
        cpf: CPF com ou sem formatação

    Returns:
        Dict com 'valid' (bool) e 'message' (str)
    """
    # Limpar CPF
    cpf_clean = clean_cpf(cpf)

    # Validar tamanho
    if len(cpf_clean) != 11:
        return {
            'valid': False,
            'message': 'CPF deve conter 11 dígitos'
        }

    # Verificar se todos os dígitos são iguais (CPF inválido)
    if cpf_clean == cpf_clean[0] * 11:
        return {
            'valid': False,
            'message': 'CPF inválido'
        }

    # Calcular primeiro dígito verificador
    soma = 0
    for i in range(9):
        soma += int(cpf_clean[i]) * (10 - i)

    resto = soma % 11
    digito1 = 0 if resto < 2 else 11 - resto

    # Verificar primeiro dígito
    if int(cpf_clean[9]) != digito1:
        return {
            'valid': False,
            'message': 'CPF inválido - dígito verificador incorreto'
        }

    # Calcular segundo dígito verificador
    soma = 0
    for i in range(10):
        soma += int(cpf_clean[i]) * (11 - i)

    resto = soma % 11
    digito2 = 0 if resto < 2 else 11 - resto

    # Verificar segundo dígito
    if int(cpf_clean[10]) != digito2:
        return {
            'valid': False,
            'message': 'CPF inválido - dígito verificador incorreto'
        }

    return {
        'valid': True,
        'message': 'CPF válido',
        'cpf_clean': cpf_clean
    }


def format_cpf(cpf: str) -> str:
    """
    Formata CPF com pontos e traço (###.###.###-##)

    Args:
        cpf: CPF apenas com números

    Returns:
        CPF formatado
    """
    cpf_clean = clean_cpf(cpf)

    if len(cpf_clean) != 11:
        return cpf

    return f"{cpf_clean[:3]}.{cpf_clean[3:6]}.{cpf_clean[6:9]}-{cpf_clean[9:]}"
