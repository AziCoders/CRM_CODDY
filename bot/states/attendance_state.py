"""FSM состояния для отметки посещаемости"""
from aiogram.fsm.state import State, StatesGroup


class AttendanceState(StatesGroup):
    """Состояния отметки посещаемости"""
    waiting_city = State()  # Выбор города (для менеджера/владельца)
    waiting_group = State()  # Выбор группы
    marking_attendance = State()  # Отметка посещаемости (интерактивная)

