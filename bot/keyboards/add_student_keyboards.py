"""Клавиатуры для добавления ученика"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters.callback_data import CallbackData
from bot.config import CITIES


class CitySelectCallback(CallbackData, prefix="city_select"):
    """Callback для выбора города при добавлении ученика"""
    city: str


class GroupSelectCallback(CallbackData, prefix="group_select"):
    """Callback для выбора группы при добавлении ученика"""
    group_id: str


class CancelCallback(CallbackData, prefix="cancel_add"):
    """Callback для отмены добавления ученика"""
    pass


def get_cities_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора города"""
    keyboard = []
    # Создаем кнопки по 2 в ряд
    for i in range(0, len(CITIES), 2):
        row = []
        row.append(InlineKeyboardButton(
            text=CITIES[i],
            callback_data=CitySelectCallback(city=CITIES[i]).pack()
        ))
        if i + 1 < len(CITIES):
            row.append(InlineKeyboardButton(
                text=CITIES[i + 1],
                callback_data=CitySelectCallback(city=CITIES[i + 1]).pack()
            ))
        keyboard.append(row)
    
    # Добавляем кнопку отмены
    keyboard.append([InlineKeyboardButton(
        text="❌ Отмена",
        callback_data=CancelCallback().pack()
    )])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_groups_keyboard(groups: list[dict]) -> InlineKeyboardMarkup:
    """Клавиатура для выбора группы с отображением количества учеников"""
    keyboard = []
    for group in groups:
        group_id = group.get("group_id")
        group_name = group.get("group_name", "Без названия")
        total_students = group.get("total_students", 0)
        
        # Формируем текст кнопки с количеством учеников
        button_text = f"{group_name} ({total_students})"
        
        keyboard.append([InlineKeyboardButton(
            text=button_text,
            callback_data=GroupSelectCallback(group_id=group_id).pack()
        )])
    
    # Добавляем кнопку отмены
    keyboard.append([InlineKeyboardButton(
        text="❌ Отмена",
        callback_data=CancelCallback().pack()
    )])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура только с кнопкой отмены"""
    keyboard = [[InlineKeyboardButton(
        text="❌ Отмена",
        callback_data=CancelCallback().pack()
    )]]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

