"""FSM состояния для регистрации"""
from aiogram.fsm.state import State, StatesGroup


class RegisterState(StatesGroup):
    """Состояния регистрации нового пользователя"""
    waiting_fio = State()

