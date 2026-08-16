"""
Regras e validações do canal de ouvidoria.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Tuple


class OuvidoriaValidationError(Exception):
    """Erro de validação para mensagens da ouvidoria."""


PROHIBITED_TERMS = {
    # Palavrões comuns (variações em texto normalizado sem acento)
    "merda",
    "porra",
    "caralho",
    "cacete",
    "puta",
    "putaquepariu",
    "foda",
    "fodase",
    "arrombado",
    "babaca",
    "otario",
    "imbecil",
    "idiota",
    "burro",
    "retardado",
    "lixo",
    "vagabundo",
    "desgracado",
    "fdp",
    "filhodaputa",
    "cuzao",
    "corno",
    "bosta",
}


def normalize_text(value: str) -> str:
    """
    Remove acentos e normaliza para comparação de termos proibidos.
    """
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_text = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return ascii_text.lower()


def validate_ouvidoria_message(content: str) -> Tuple[str, str]:
    """
    Valida conteúdo da mensagem e retorna (conteudo_original_limpo, conteudo_normalizado).
    """
    clean_content = (content or "").strip()
    if len(clean_content) < 10:
        raise OuvidoriaValidationError("Mensagem muito curta. Descreva melhor sua manifestação.")
    if len(clean_content) > 1000:
        raise OuvidoriaValidationError("Mensagem muito longa. Limite máximo: 1000 caracteres.")

    normalized = normalize_text(clean_content)
    tokens = re.findall(r"[a-z0-9]+", normalized)
    compact = "".join(tokens)

    for term in PROHIBITED_TERMS:
        if term in tokens or term in compact:
            raise OuvidoriaValidationError(
                "Mensagem contém linguagem ofensiva (palavrões/xingamentos). "
                "Reescreva de forma respeitosa para publicar."
            )

    return clean_content, normalized
