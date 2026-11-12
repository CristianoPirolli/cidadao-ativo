"""
Filtros de template customizados do Cidadão Ativo.
"""
import json
import os
from zoneinfo import ZoneInfo

from django import template
from django.utils.safestring import mark_safe

register = template.Library()

_JSON_SCRIPT_ESCAPES = {
    ord('<'): '\\u003c',
    ord('>'): '\\u003e',
    ord('&'): '\\u0026',
    ord("'"): '\\u0027',
    0x2028: '\\u2028',
    0x2029: '\\u2029',
}


@register.filter
def tojson(value):
    """Serializa valor para JSON seguro de embutir em <script>."""
    return mark_safe(json.dumps(value, default=str).translate(_JSON_SCRIPT_ESCAPES))


@register.filter
def basename(path):
    """Retorna o nome do arquivo a partir de um caminho."""
    if not path:
        return ''
    return os.path.basename(path)

SP_TZ = ZoneInfo('America/Sao_Paulo')


@register.filter
def format_datetime_sp(value, fmt='%d/%m/%Y %H:%M'):
    """Formata datetime para o fuso horário de São Paulo."""
    if not value:
        return '-'
    try:
        if hasattr(value, 'tzinfo') and value.tzinfo is not None:
            value = value.astimezone(SP_TZ)
        return value.strftime(fmt)
    except Exception:
        return str(value)


@register.filter
def format_duration(seconds):
    """Formata duração em segundos para formato legível."""
    if seconds is None:
        return '-'
    try:
        seconds = int(seconds)
        if seconds < 60:
            return f'{seconds}s'
        elif seconds < 3600:
            return f'{seconds // 60}min'
        elif seconds < 86400:
            h = seconds // 3600
            m = (seconds % 3600) // 60
            return f'{h}h {m}min' if m else f'{h}h'
        else:
            d = seconds // 86400
            h = (seconds % 86400) // 3600
            return f'{d}d {h}h' if h else f'{d}d'
    except Exception:
        return str(seconds)
