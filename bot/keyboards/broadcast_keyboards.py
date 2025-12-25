"""Клавиатуры для рассылок"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters.callback_data import CallbackData
from typing import List, Dict


class BroadcastCallback(CallbackData, prefix="broadcast"):
    """Callback для рассылок"""
    action: str  # all, select, back, confirm, cancel


class BroadcastSelectUserCallback(CallbackData, prefix="broadcast_user"):
    """Callback для выбора пользователя в рассылке"""
    user_id: int
    action: str  # toggle


class BroadcastConfirmCallback(CallbackData, prefix="broadcast_confirm"):
    """Callback для подтверждения рассылки"""
    action: str  # confirm, cancel


def get_broadcast_main_keyboard() -> InlineKeyboardMarkup:
    """Главная клавиатура рассылок"""
    keyboard = [
        [InlineKeyboardButton(
            text="📢 Всем сотрудникам",
            callback_data=BroadcastCallback(action="all").pack()
        )],
        [InlineKeyboardButton(
            text="👥 Выборочная рассылка",
            callback_data=BroadcastCallback(action="select").pack()
        )],
        [InlineKeyboardButton(
            text="❌ Отмена",
            callback_data=BroadcastCallback(action="back").pack()
        )],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_broadcast_users_keyboard(
    users: List[Dict],
    selected_users: List[int],
    page: int = 0,
    page_size: int = 10
) -> InlineKeyboardMarkup:
    """Клавиатура для выбора пользователей в рассылке"""
    keyboard = []
    
    # Вычисляем границы страницы
    start_idx = page * page_size
    end_idx = min(start_idx + page_size, len(users))
    page_users = users[start_idx:end_idx]
    
    # Кнопки выбора пользователей
    for user in page_users:
        user_id = user.get("user_id")
        fio = user.get("fio", "N/A")
        role = user.get("role", "")
        
        # Иконки ролей
        role_icons = {
            "owner": "👑",
            "manager": "👨‍💼",
            "teacher": "👨‍🏫",
            "smm": "📱"
        }
        role_icon = role_icons.get(role, "👤")
        
        # Статус выбора
        is_selected = user_id in selected_users
        checkbox = "✅" if is_selected else "☐"
        
        keyboard.append([InlineKeyboardButton(
            text=f"{checkbox} {role_icon} {fio}",
            callback_data=BroadcastSelectUserCallback(
                user_id=user_id,
                action="toggle"
            ).pack()
        )])
    
    # Кнопки пагинации
    nav_buttons = []
    total_pages = (len(users) + page_size - 1) // page_size
    
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(
            text="◀️ Назад",
            callback_data=BroadcastCallback(action=f"page_{page - 1}").pack()
        ))
    
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(
            text="Вперед ▶️",
            callback_data=BroadcastCallback(action=f"page_{page + 1}").pack()
        ))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # Кнопки действий
    keyboard.append([InlineKeyboardButton(
        text=f"✅ Отправить ({len(selected_users)} получателей)",
        callback_data=BroadcastCallback(action="confirm").pack()
    )])
    
    keyboard.append([InlineKeyboardButton(
        text="❌ Отмена",
        callback_data=BroadcastCallback(action="back").pack()
    )])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_broadcast_confirm_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения рассылки"""
    keyboard = [
        [InlineKeyboardButton(
            text="✅ Отправить",
            callback_data=BroadcastConfirmCallback(action="confirm").pack()
        )],
        [InlineKeyboardButton(
            text="❌ Отмена",
            callback_data=BroadcastConfirmCallback(action="cancel").pack()
        )],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

