"""FSM состояния для управления ролями"""
from aiogram.fsm.state import State, StatesGroup


class RoleManagementState(StatesGroup):
    """Состояния управления ролями"""
    waiting_user_id = State()  # Ожидание ID пользователя для добавления роли
    waiting_role = State()  # Ожидание выбора роли
    waiting_city = State()  # Ожидание выбора города (для преподавателя)

