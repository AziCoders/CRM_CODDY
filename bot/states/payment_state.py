"""FSM состояния для отметки оплаты"""
from aiogram.fsm.state import State, StatesGroup


class PaymentState(StatesGroup):
    """Состояния отметки оплаты"""
    waiting_city = State()  # Выбор города (для меню оплаты)
    waiting_student = State()  # Выбор ученика из списка
    waiting_status = State()  # Выбор статуса оплаты
    waiting_comment = State()  # Ввод комментария

