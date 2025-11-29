"""Клавиатуры для синхронизации"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters.callback_data import CallbackData
from bot.config import CITIES


class SyncCityCallback(CallbackData, prefix="sync_city"):
    """Callback для выбора города при синхронизации"""
    city: str  # Название города или "all" для всех городов


class SyncTypeCallback(CallbackData, prefix="sync_type"):
    """Callback для выбора типа синхронизации"""
    sync_type: str  # attendance, payments, groups, main_info, full


class SyncBackCallback(CallbackData, prefix="sync_back"):
    """Callback для возврата"""
    pass


def get_sync_cities_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора города при синхронизации"""
    keyboard = []
    
    # Кнопка "Все города"
    keyboard.append([InlineKeyboardButton(
        text="🌍 Все города",
        callback_data=SyncCityCallback(city="all").pack()
    )])
    
    # Кнопки городов по 2 в ряд
    for i in range(0, len(CITIES), 2):
        row = []
        row.append(InlineKeyboardButton(
            text=CITIES[i],
            callback_data=SyncCityCallback(city=CITIES[i]).pack()
        ))
        if i + 1 < len(CITIES):
            row.append(InlineKeyboardButton(
                text=CITIES[i + 1],
                callback_data=SyncCityCallback(city=CITIES[i + 1]).pack()
            ))
        keyboard.append(row)
    
    # Кнопка "Отмена"
    keyboard.append([InlineKeyboardButton(
        text="❌ Отмена",
        callback_data=SyncBackCallback().pack()
    )])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_sync_type_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора типа синхронизации"""
    keyboard = [
        [InlineKeyboardButton(
            text="📊 Посещаемость",
            callback_data=SyncTypeCallback(sync_type="attendance").pack()
        )],
        [InlineKeyboardButton(
            text="💰 Оплаты",
            callback_data=SyncTypeCallback(sync_type="payments").pack()
        )],
        [InlineKeyboardButton(
            text="👥 Группы",
            callback_data=SyncTypeCallback(sync_type="groups").pack()
        )],
        [InlineKeyboardButton(
            text="ℹ️ Главная информация",
            callback_data=SyncTypeCallback(sync_type="main_info").pack()
        )],
        [InlineKeyboardButton(
            text="🔄 Полная синхронизация",
            callback_data=SyncTypeCallback(sync_type="full").pack()
        )],
        [InlineKeyboardButton(
            text="🔙 Назад",
            callback_data=SyncBackCallback().pack()
        )]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

