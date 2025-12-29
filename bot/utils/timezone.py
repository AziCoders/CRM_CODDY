"""Утилита для работы с часовым поясом МСК (Московское время) и UTC"""
from datetime import datetime, timezone

try:
    # Python 3.9+
    from zoneinfo import ZoneInfo
except ImportError:
    # Python 3.8 и ниже - требуется backports.zoneinfo
    try:
        from backports.zoneinfo import ZoneInfo
    except ImportError:
        raise ImportError(
            "Для работы с часовыми поясами требуется Python 3.9+ или пакет backports.zoneinfo. "
            "Установите: pip install backports.zoneinfo"
        )

# Московское время (UTC+3)
MSK_TIMEZONE = ZoneInfo("Europe/Moscow")


def get_msk_now() -> datetime:
    """
    Возвращает текущее время в часовом поясе МСК
    
    Returns:
        datetime объект с часовым поясом МСК
    """
    return datetime.now(MSK_TIMEZONE)


def get_msk_time() -> datetime.time:
    """
    Возвращает текущее время (только time) в часовом поясе МСК
    
    Returns:
        time объект с текущим временем МСК
    """
    return get_msk_now().time()


def get_utc_time() -> datetime.time:
    """
    Возвращает текущее время (только time) в часовом поясе UTC
    
    Returns:
        time объект с текущим временем UTC
    """
    return datetime.now(timezone.utc).time()


def get_msk_date() -> datetime.date:
    """
    Возвращает текущую дату в часовом поясе МСК
    
    Returns:
        date объект с текущей датой МСК
    """
    return get_msk_now().date()


def format_date_msk(date_obj: datetime = None) -> str:
    """
    Форматирует дату в формат дд.мм.гггг для МСК
    
    Args:
        date_obj: Объект datetime (если None, используется текущая дата МСК)
        
    Returns:
        Строка в формате "дд.мм.гггг"
    """
    if date_obj is None:
        date_obj = get_msk_now()
    elif date_obj.tzinfo is None:
        # Если datetime без часового пояса, предполагаем что это МСК
        date_obj = date_obj.replace(tzinfo=MSK_TIMEZONE)
    
    # Конвертируем в МСК если нужно
    if date_obj.tzinfo != MSK_TIMEZONE:
        date_obj = date_obj.astimezone(MSK_TIMEZONE)
    
    return date_obj.strftime("%d.%m.%Y")


def format_datetime_str_msk(date_obj: datetime = None, format_str: str = "%Y-%m-%d") -> str:
    """
    Форматирует дату/время в строку для МСК
    
    Args:
        date_obj: Объект datetime (если None, используется текущая дата/время МСК)
        format_str: Формат строки (по умолчанию "%Y-%m-%d")
        
    Returns:
        Отформатированная строка
    """
    if date_obj is None:
        date_obj = get_msk_now()
    elif date_obj.tzinfo is None:
        # Если datetime без часового пояса, предполагаем что это МСК
        date_obj = date_obj.replace(tzinfo=MSK_TIMEZONE)
    
    # Конвертируем в МСК если нужно
    if date_obj.tzinfo != MSK_TIMEZONE:
        date_obj = date_obj.astimezone(MSK_TIMEZONE)
    
    return date_obj.strftime(format_str)

