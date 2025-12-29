"""Клавиатуры для отчетов"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters.callback_data import CallbackData
from bot.config import CITIES


class ReportTypeCallback(CallbackData, prefix="report_type"):
    """Callback для выбора типа отчета"""
    report_type: str  # summary, city_attendance, groups_attendance, payments
    city: str = ""  # Город для отчета


class ReportCityCallback(CallbackData, prefix="report_city"):
    """Callback для выбора города в отчетах"""
    city: str  # Название города


class PaymentsPaginationCallback(CallbackData, prefix="payments_page"):
    """Callback для пагинации отчета по оплатам"""
    city: str  # Название города
    page: int  # Номер страницы (начинается с 0)


class GroupAttendanceCallback(CallbackData, prefix="grp_att"):
    """Callback для выбора группы для детального отчета по посещаемости"""
    city: str  # Название города (сокращенное)
    idx: int  # Индекс группы в списке


def get_report_city_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора города (для владельца)"""
    keyboard = []
    
    # Кнопка "Все города" для общего отчета
    keyboard.append([InlineKeyboardButton(
        text="🌍 Все города (Общий отчет)",
        callback_data=ReportCityCallback(city="all").pack()
    )])
    
    # Создаем кнопки по 2 в ряд
    for i in range(0, len(CITIES), 2):
        row = []
        row.append(InlineKeyboardButton(
            text=CITIES[i],
            callback_data=ReportCityCallback(city=CITIES[i]).pack()
        ))
        if i + 1 < len(CITIES):
            row.append(InlineKeyboardButton(
                text=CITIES[i + 1],
                callback_data=ReportCityCallback(city=CITIES[i + 1]).pack()
            ))
        keyboard.append(row)
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_report_keyboard(city: str = "", is_owner: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура для выбора типа отчета
    
    Args:
        city: Название города
        is_owner: True для владельца и менеджера (показывать отчет по оплатам)
    """
    keyboard = [
        [InlineKeyboardButton(
            text="📊 Сводка по городу",
            callback_data=ReportTypeCallback(report_type="summary", city=city).pack()
        )],
        [InlineKeyboardButton(
            text="📋 Посещаемость по группам",
            callback_data=ReportTypeCallback(report_type="groups_attendance", city=city).pack()
        )],
    ]
    
    # Для владельца и менеджера добавляем отчет по оплатам
    if is_owner:
        keyboard.append([InlineKeyboardButton(
            text="💰 Отчет по оплатам",
            callback_data=ReportTypeCallback(report_type="payments", city=city).pack()
        )])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_groups_keyboard(city_short: str, groups: list) -> InlineKeyboardMarkup:
    """Клавиатура для выбора группы в отчете по посещаемости"""
    keyboard = []
    
    # Создаем кнопки по 2 в ряд
    for i in range(0, len(groups), 2):
        row = []
        group1 = groups[i]
        row.append(InlineKeyboardButton(
            text=group1["group_name"],
            callback_data=GroupAttendanceCallback(city=city_short, idx=i).pack()
        ))
        if i + 1 < len(groups):
            group2 = groups[i + 1]
            row.append(InlineKeyboardButton(
                text=group2["group_name"],
                callback_data=GroupAttendanceCallback(city=city_short, idx=i + 1).pack()
            ))
        keyboard.append(row)
    
    # Кнопка возврата к отчетам (используем полное название из кэша)
    keyboard.append([InlineKeyboardButton(
        text="🔙 Назад к отчетам",
        callback_data=ReportTypeCallback(report_type="back_to_menu", city=city_short).pack()
    )])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_payments_pagination_keyboard(city: str, page: int, has_prev: bool, has_next: bool) -> InlineKeyboardMarkup:
    """Клавиатура для пагинации отчета по оплатам"""
    keyboard = []
    buttons = []
    
    if has_prev:
        buttons.append(InlineKeyboardButton(
            text="◀️ Назад",
            callback_data=PaymentsPaginationCallback(city=city, page=page - 1).pack()
        ))
    
    if has_next:
        buttons.append(InlineKeyboardButton(
            text="Вперед ▶️",
            callback_data=PaymentsPaginationCallback(city=city, page=page + 1).pack()
        ))
    
    if buttons:
        keyboard.append(buttons)
    
    # Кнопка возврата к меню отчетов (используем специальный тип для возврата)
    keyboard.append([InlineKeyboardButton(
        text="🔙 Назад к отчетам",
        callback_data=ReportTypeCallback(report_type="back_to_menu", city=city).pack()
    )])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

