"""FSM состояния для рассылок"""
from aiogram.fsm.state import State, StatesGroup


class BroadcastState(StatesGroup):
    """Состояния рассылок"""
    waiting_message = State()  # Ожидание текста сообщения для рассылки

