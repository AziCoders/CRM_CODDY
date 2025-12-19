"""FSM состояния для удаления ученика"""
from aiogram.fsm.state import State, StatesGroup


class DeleteStudentState(StatesGroup):
    """Состояния удаления ученика"""
    waiting_reason = State()  # Ввод причины ухода

