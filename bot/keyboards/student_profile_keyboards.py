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


def get_student_profile_keyboard(student_id: str, city: str, group_id: str = "") -> InlineKeyboardMarkup:
    """Клавиатура с кнопками Оплата и Удалить для профиля ученика"""
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
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

