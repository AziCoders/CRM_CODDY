"""Клавиатуры для напоминаний о платежах"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters.callback_data import CallbackData
from typing import Dict, List


class PaymentReminderCategoryCallback(CallbackData, prefix="pmt_rem_cat"):
    """Callback для переключения категории напоминаний о платежах"""
    category: int  # 0 - сегодня, 1 - через 1 день, 2 - через 2 дня, 3 - через 3 дня
    message_id: int


class PaymentReminderRefreshCallback(CallbackData, prefix="pmt_rem_refresh"):
    """Callback для обновления отчета о платежах"""
    message_id: int


def get_payment_reminder_keyboard(
    current_category: int,
    available_categories: List[int],
    message_id: int
) -> InlineKeyboardMarkup:
    """
    Клавиатура для навигации по категориям напоминаний о платежах
    
    Args:
        current_category: Текущая категория (0-3)
        available_categories: Список доступных категорий с учениками
        message_id: ID сообщения для обновления
    """
    keyboard = []
    
    # Заголовки категорий
    category_labels = {
        0: "📅 Сегодня",
        1: "📅 Через 1 день",
        2: "📅 Через 2 дня",
        3: "📅 Через 3 дня"
    }
    
    # Создаем кнопки категорий - только те, где есть ученики
    category_row_1 = []  # Первая строка: сегодня и через 1 день
    category_row_2 = []  # Вторая строка: через 2 дня и через 3 дня
    
    # Формируем первую строку (сегодня и через 1 день)
    for cat in [0, 1]:
        if cat in available_categories:
            label = category_labels[cat]
            # Если это текущая категория, добавляем отметку
            if cat == current_category:
                label = f"✓ {label}"
            
            category_row_1.append(InlineKeyboardButton(
                text=label,
                callback_data=PaymentReminderCategoryCallback(
                    category=cat,
                    message_id=message_id
                ).pack()
            ))
    
    # Формируем вторую строку (через 2 дня и через 3 дня)
    for cat in [2, 3]:
        if cat in available_categories:
            label = category_labels[cat]
            # Если это текущая категория, добавляем отметку
            if cat == current_category:
                label = f"✓ {label}"
            
            category_row_2.append(InlineKeyboardButton(
                text=label,
                callback_data=PaymentReminderCategoryCallback(
                    category=cat,
                    message_id=message_id
                ).pack()
            ))
    
    # Добавляем строки категорий только если в них есть кнопки
    if category_row_1:
        keyboard.append(category_row_1)
    if category_row_2:
        keyboard.append(category_row_2)
    
    # Кнопка обновления
    keyboard.append([InlineKeyboardButton(
        text="🔄 Обновить",
        callback_data=PaymentReminderRefreshCallback(message_id=message_id).pack()
    )])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
