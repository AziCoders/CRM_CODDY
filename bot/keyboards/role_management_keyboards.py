"""Клавиатуры для управления ролями"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters.callback_data import CallbackData
from bot.config import CITIES


class RoleManagementCallback(CallbackData, prefix="role_mgmt"):
    """Callback для управления ролями"""
    action: str  # view, add, delete, back


class RoleDeleteCallback(CallbackData, prefix="role_delete"):
    """Callback для удаления роли"""
    user_id: int


class RoleEditCallback(CallbackData, prefix="role_edit"):
    """Callback для редактирования роли"""
    user_id: int


def get_role_management_keyboard() -> InlineKeyboardMarkup:
    """Главная клавиатура управления ролями"""
    keyboard = [
        [InlineKeyboardButton(
            text="👥 Просмотр работников",
            callback_data=RoleManagementCallback(action="view").pack()
        )],
        [InlineKeyboardButton(
            text="➕ Добавить роль",
            callback_data=RoleManagementCallback(action="add").pack()
        )],
        [InlineKeyboardButton(
            text="🔙 Назад",
            callback_data=RoleManagementCallback(action="back").pack()
        )]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_users_list_keyboard(users: list, page: int = 0, page_size: int = 10) -> InlineKeyboardMarkup:
    """Клавиатура со списком пользователей с пагинацией"""
    keyboard = []
    
    total_pages = (len(users) + page_size - 1) // page_size
    start_idx = page * page_size
    end_idx = min(start_idx + page_size, len(users))
    page_users = users[start_idx:end_idx]
    
    # Кнопки пользователей
    for user in page_users:
        user_id = user.get("user_id")
        fio = user.get("fio", "Без имени")
        role = user.get("role", "N/A")
        role_emoji = {
            "owner": "👑",
            "manager": "👨‍💼",
            "teacher": "👨‍🏫",
            "smm": "📱",
            "pending": "⏳"
        }.get(role, "👤")
        
        button_text = f"{role_emoji} {fio} ({role})"
        keyboard.append([InlineKeyboardButton(
            text=button_text,
            callback_data=RoleEditCallback(user_id=user_id).pack()
        )])
    
    # Кнопки пагинации
    pagination_row = []
    if page > 0:
        pagination_row.append(InlineKeyboardButton(
            text="◀️ Назад",
            callback_data=RoleManagementCallback(action=f"view_page_{page - 1}").pack()
        ))
    
    if page < total_pages - 1:
        pagination_row.append(InlineKeyboardButton(
            text="Вперед ▶️",
            callback_data=RoleManagementCallback(action=f"view_page_{page + 1}").pack()
        ))
    
    if pagination_row:
        keyboard.append(pagination_row)
    
    # Кнопка "Назад"
    keyboard.append([InlineKeyboardButton(
        text="🔙 Назад",
        callback_data=RoleManagementCallback(action="back").pack()
    )])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_user_actions_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Клавиатура действий с пользователем"""
    keyboard = [
        [InlineKeyboardButton(
            text="🗑️ Удалить роль",
            callback_data=RoleDeleteCallback(user_id=user_id).pack()
        )],
        [InlineKeyboardButton(
            text="🔙 Назад к списку",
            callback_data=RoleManagementCallback(action="view").pack()
        )]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_confirm_delete_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения удаления"""
    keyboard = [
        [
            InlineKeyboardButton(
                text="✅ Подтвердить",
                callback_data=RoleDeleteCallback(user_id=user_id).pack()
            ),
            InlineKeyboardButton(
                text="❌ Отмена",
                callback_data=RoleEditCallback(user_id=user_id).pack()
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

