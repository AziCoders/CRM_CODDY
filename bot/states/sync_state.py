"""FSM состояния для синхронизации"""
from aiogram.fsm.state import State, StatesGroup


class SyncState(StatesGroup):
    """Состояния синхронизации"""
    waiting_city = State()  # Выбор города или "Все города"
    waiting_sync_type = State()  # Выбор типа синхронизации для города

