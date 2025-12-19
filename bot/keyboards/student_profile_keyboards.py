"""Клавиатуры для профиля ученика"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters.callback_data import CallbackData


class StudentPaymentCallback(CallbackData, prefix="sp"):
    """Callback для оплаты ученика из профиля"""
    student_id: str
    city_en: str  # Используем английское название города для экономии места


class StudentDeleteCallback(CallbackData, prefix="sd"):
    """Callback для удаления ученика из профиля"""
    student_id: str
    city_en: str  # Используем английское название города для экономии места
    group_id: str = ""


class CancelDeleteCallback(CallbackData, prefix="cancel_delete"):
    """Callback для отмены удаления ученика"""
    pass


class StudentAttendanceCallback(CallbackData, prefix="sa"):
    """Callback для просмотра посещаемости ученика"""
    student_id: str
    city_en: str


class BackToStudentsCallback(CallbackData, prefix="bts"):
    """Callback для возврата к списку учеников группы"""
    group_id: str  # Сокращенный ID группы (первые 10 символов)
    city_en: str  # Английское название города (сокращенное до 6 символов)


def get_student_profile_keyboard(student_id: str, city: str, group_id: str = "", show_back: bool = False) -> InlineKeyboardMarkup:
    """
    Клавиатура с кнопками Оплата, Удалить и Просмотр посещаемости для профиля ученика
    
    Args:
        student_id: ID ученика
        city: Название города
        group_id: ID группы (опционально)
        show_back: Показывать ли кнопку "Назад" (только если профиль получен через кнопки)
    """
    from bot.config import CITY_MAPPING
    # Используем английское название города для callback_data, сокращаем до 6 символов
    city_en = CITY_MAPPING.get(city, city)[:6]
    
    # Убираем дефисы из UUID и сокращаем до 16 символов для экономии места
    # Первые 16 символов UUID обычно достаточно уникальны
    student_id_short = student_id.replace("-", "")[:16] if student_id else ""
    group_id_short = group_id.replace("-", "")[:10] if group_id else ""
    
    keyboard = [
        [
            InlineKeyboardButton(
                text="💰 Оплата",
                callback_data=StudentPaymentCallback(student_id=student_id_short, city_en=city_en).pack()
            ),
            InlineKeyboardButton(
                text="🗑️ Удалить",
                callback_data=StudentDeleteCallback(student_id=student_id_short, city_en=city_en, group_id=group_id_short).pack()
            )
        ],
        [
            InlineKeyboardButton(
                text="📊 Просмотр посещаемости",
                callback_data=StudentAttendanceCallback(student_id=student_id_short, city_en=city_en).pack()
            )
        ]
    ]
    
    # Добавляем кнопку "Назад" только если профиль получен через кнопки
    if show_back and group_id_short:
        keyboard.append([
            InlineKeyboardButton(
                text="◀️ Назад",
                callback_data=BackToStudentsCallback(group_id=group_id_short, city_en=city_en).pack()
            )
        ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_cancel_delete_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура только с кнопкой отмены удаления"""
    keyboard = [[InlineKeyboardButton(
        text="❌ Отмена",
        callback_data=CancelDeleteCallback().pack()
    )]]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

