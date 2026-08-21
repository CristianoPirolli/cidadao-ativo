"""
Utilitários para manipulação de timezone.

Sistema usa UTC no banco de dados e converte para America/Sao_Paulo (UTC-3) na exibição.
"""

from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo


# Timezone de São Paulo (UTC-3)
SAO_PAULO_TZ = ZoneInfo('America/Sao_Paulo')
UTC_TZ = ZoneInfo('UTC')


def get_sao_paulo_tz():
    """
    Retorna o timezone de São Paulo (America/Sao_Paulo).

    Nota: São Paulo está em UTC-3 o ano todo (sem horário de verão desde 2019).
    """
    return SAO_PAULO_TZ


def utcnow_sp():
    """
    Retorna o datetime atual no timezone de São Paulo (UTC-3).

    Returns:
        datetime: Datetime atual com timezone America/Sao_Paulo
    """
    return datetime.now(SAO_PAULO_TZ)


def to_sao_paulo(utc_datetime):
    """
    Converte um datetime UTC para o timezone de São Paulo.

    Args:
        utc_datetime: datetime em UTC (naive ou aware)

    Returns:
        datetime: Datetime convertido para America/Sao_Paulo

    Examples:
        >>> from datetime import datetime
        >>> utc_dt = datetime(2024, 1, 15, 12, 0, 0)  # UTC
        >>> sp_dt = to_sao_paulo(utc_dt)
        >>> sp_dt.hour  # 9 (12 - 3)
    """
    if utc_datetime is None:
        return None

    # Se já tem timezone, converte para UTC primeiro
    if utc_datetime.tzinfo is not None:
        utc_datetime = utc_datetime.astimezone(UTC_TZ)
    else:
        # Se é naive, assume que é UTC
        utc_datetime = utc_datetime.replace(tzinfo=UTC_TZ)

    # Converte para São Paulo
    return utc_datetime.astimezone(SAO_PAULO_TZ)


def to_utc(sp_datetime):
    """
    Converte um datetime de São Paulo para UTC.

    Args:
        sp_datetime: datetime em America/Sao_Paulo (naive ou aware)

    Returns:
        datetime: Datetime convertido para UTC

    Examples:
        >>> from datetime import datetime
        >>> sp_dt = datetime(2024, 1, 15, 9, 0, 0)  # São Paulo
        >>> utc_dt = to_utc(sp_dt)
        >>> utc_dt.hour  # 12 (9 + 3)
    """
    if sp_datetime is None:
        return None

    # Se já tem timezone, converte para SP primeiro
    if sp_datetime.tzinfo is not None:
        sp_datetime = sp_datetime.astimezone(SAO_PAULO_TZ)
    else:
        # Se é naive, assume que é São Paulo
        sp_datetime = sp_datetime.replace(tzinfo=SAO_PAULO_TZ)

    # Converte para UTC
    return sp_datetime.astimezone(UTC_TZ)


def format_datetime_sp(utc_datetime, format_str='%d/%m/%Y %H:%M'):
    """
    Formata um datetime UTC para string no timezone de São Paulo.

    Esta função é usada como filtro Jinja2 nos templates.

    Args:
        utc_datetime: datetime em UTC (geralmente do banco de dados)
        format_str: formato strftime desejado

    Returns:
        str: String formatada no timezone de São Paulo

    Examples:
        >>> from datetime import datetime
        >>> utc_dt = datetime(2024, 1, 15, 12, 0, 0)  # 12:00 UTC
        >>> format_datetime_sp(utc_dt)
        '15/01/2024 09:00'  # 09:00 em São Paulo (UTC-3)
    """
    if utc_datetime is None:
        return '-'

    sp_datetime = to_sao_paulo(utc_datetime)
    return sp_datetime.strftime(format_str)


def format_duration(seconds: Optional[float]) -> str:
    """
    Formata um tempo em segundos para uma string legível (dias, horas, minutos).
    """
    if seconds is None:
        return '-'

    base = max(int(round(seconds)), 0)
    days, remainder = divmod(base, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes = remainder // 60

    parts = []
    if days:
        parts.append(f"{days} dia{'s' if days != 1 else ''}")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}min")

    if not parts:
        parts.append("menos de 1 min")

    return ' '.join(parts)
