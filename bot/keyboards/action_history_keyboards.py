"""Клавиатуры для истории действий"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters.callback_data import CallbackData
from bot.config import CITIES


class ActionHistoryCallback(CallbackData, prefix="action_history"):
    """Callback для истории действий"""
    action: str  # view_all, filter, back


class ActionHistoryFilterCallback(CallbackData, prefix="action_filter"):
    """Callback для фильтров истории"""
    filter_type: str  # action_type, user_id, city
    filter_value: str


def get_action_history_keyboard() -> InlineKeyboardMarkup:
    """Главная клавиатура истории действий"""
    keyboard = [
        [InlineKeyboardButton(
            text="📋 Просмотр всех действий",
            callback_data=ActionHistoryCallback(action="view_all").pack()
        )],
        [InlineKeyboardButton(
            text="🔍 Фильтры",
            callback_data=ActionHistoryCallback(action="filter").pack()
        )],
        [InlineKeyboardButton(
            text="🔙 Назад",
            callback_data=ActionHistoryCallback(action="back").pack()
        )]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_action_history_filter_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура фильтров истории"""
    keyboard = [
        [InlineKeyboardButton(
            text="➕ Добавление ученика",
            callback_data=ActionHistoryFilterCallback(filter_type="action_type", filter_value="add_student").pack()
        )],
        [InlineKeyboardButton(
            text="📝 Посещаемость",
            callback_data=ActionHistoryFilterCallback(filter_type="action_type", filter_value="mark_attendance").pack()
        )],
        [InlineKeyboardButton(
            text="💰 Оплаты",
            callback_data=ActionHistoryFilterCallback(filter_type="action_type", filter_value="update_payment").pack()
        )],
        [InlineKeyboardButton(
            text="👤 Управление ролями",
            callback_data=ActionHistoryFilterCallback(filter_type="action_type", filter_value="add_role").pack()
        )],
        [InlineKeyboardButton(
            text="📊 Отчеты",
            callback_data=ActionHistoryFilterCallback(filter_type="action_type", filter_value="generate_report").pack()
        )],
        [InlineKeyboardButton(
            text="🔄 Синхронизация",
            callback_data=ActionHistoryFilterCallback(filter_type="action_type", filter_value="sync_data").pack()
        )],
        [InlineKeyboardButton(
            text="🔙 Назад",
            callback_data=ActionHistoryCallback(action="back").pack()
        )]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

