"""FSM состояния для добавления ученика"""
from aiogram.fsm.state import State, StatesGroup


class AddStudentState(StatesGroup):
    """Состояния добавления нового ученика"""
    waiting_city = State()  # Выбор города
    waiting_group = State()  # Выбор группы
    waiting_data = State()  # Ввод данных ученика

