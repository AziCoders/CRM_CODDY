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


class RoleUpdateRoleCallback(CallbackData, prefix="role_update_role"):
    """Callback для изменения роли пользователя"""
    user_id: int


class RoleUpdateCityCallback(CallbackData, prefix="role_update_city"):
    """Callback для изменения города пользователя"""
    user_id: int


class RoleUpdateRoleSelectCallback(CallbackData, prefix="role_update_role_select"):
    """Callback для выбора роли при обновлении"""
    user_id: int
    role: str


class RoleUpdateCitySelectCallback(CallbackData, prefix="role_update_city_select"):
    """Callback для выбора города при обновлении"""
    user_id: int
    city: str


class RoleUpdateCancelCallback(CallbackData, prefix="role_update_cancel"):
    """Callback для отмены обновления"""
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
            text="✏️ Изменить роль",
            callback_data=RoleUpdateRoleCallback(user_id=user_id).pack()
        )],
        [InlineKeyboardButton(
            text="🏙️ Изменить город",
            callback_data=RoleUpdateCityCallback(user_id=user_id).pack()
        )],
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


def get_role_update_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Клавиатура выбора роли для обновления"""
    keyboard = [
        [InlineKeyboardButton(
            text="👨‍💼 Менеджер",
            callback_data=RoleUpdateRoleSelectCallback(user_id=user_id, role="manager").pack()
        )],
        [InlineKeyboardButton(
            text="👨‍🏫 Преподаватель",
            callback_data=RoleUpdateRoleSelectCallback(user_id=user_id, role="teacher").pack()
        )],
        [InlineKeyboardButton(
            text="📱 SMM",
            callback_data=RoleUpdateRoleSelectCallback(user_id=user_id, role="smm").pack()
        )],
        [InlineKeyboardButton(
            text="❌ Отмена",
            callback_data=RoleUpdateCancelCallback(user_id=user_id).pack()
        )]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_city_update_keyboard(user_id: int, include_all: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура выбора города для обновления"""
    keyboard = []
    
    # Добавляем опцию "Все города" если разрешено
    if include_all:
        keyboard.append([InlineKeyboardButton(
            text="🌍 Все города",
            callback_data=RoleUpdateCitySelectCallback(user_id=user_id, city="all").pack()
        )])
    
    # Добавляем кнопки для каждого города
    for city in CITIES:
        keyboard.append([InlineKeyboardButton(
            text=f"🏙️ {city}",
            callback_data=RoleUpdateCitySelectCallback(user_id=user_id, city=city).pack()
        )])
    
    # Кнопка отмены
    keyboard.append([InlineKeyboardButton(
        text="❌ Отмена",
        callback_data=RoleUpdateCancelCallback(user_id=user_id).pack()
    )])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

