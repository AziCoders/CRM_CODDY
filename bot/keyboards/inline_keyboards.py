"""Inline клавиатуры для бота"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters.callback_data import CallbackData
from bot.config import CITIES


class RoleCallback(CallbackData, prefix="role"):
    """Callback для выбора роли"""
    role: str  # teacher, manager, smm
    user_id: int


class CityCallback(CallbackData, prefix="city"):
    """Callback для выбора города"""
    user_id: int
    city: str


def get_role_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для выбора роли владельцем"""
    keyboard = [
        [InlineKeyboardButton(
            text="Преподаватель",
            callback_data=RoleCallback(role="teacher", user_id=user_id).pack()
        )],
        [InlineKeyboardButton(
            text="Менеджер",
            callback_data=RoleCallback(role="manager", user_id=user_id).pack()
        )],
        [InlineKeyboardButton(
            text="SMM",
            callback_data=RoleCallback(role="smm", user_id=user_id).pack()
        )],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_city_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для выбора города (для преподавателя)"""
    keyboard = []
    # Создаем кнопки по 2 в ряд
    for i in range(0, len(CITIES), 2):
        row = []
        row.append(InlineKeyboardButton(
            text=CITIES[i],
            callback_data=CityCallback(user_id=user_id, city=CITIES[i]).pack()
        ))
        if i + 1 < len(CITIES):
            row.append(InlineKeyboardButton(
                text=CITIES[i + 1],
                callback_data=CityCallback(user_id=user_id, city=CITIES[i + 1]).pack()
            ))
        keyboard.append(row)
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

