"""Reply клавиатуры для разных ролей"""
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def get_owner_menu() -> ReplyKeyboardMarkup:
    """Меню для владельца"""
    keyboard = [
        [KeyboardButton(text="Управление ролями"), KeyboardButton(text="История действий")],
        [KeyboardButton(text="Добавить ученика"), KeyboardButton(text="Посещаемость")],
        [KeyboardButton(text="Оплаты"), KeyboardButton(text="Города")],
        [KeyboardButton(text="Синхронизация"), KeyboardButton(text="Отчёты")],
        [KeyboardButton(text="ИИ-отчёт"), KeyboardButton(text="Информация")],
        [KeyboardButton(text="Отчет по сотрудникам"), KeyboardButton(text="Рассылка")],
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        input_field_placeholder="Выберите действие"
    )


def get_manager_menu() -> ReplyKeyboardMarkup:
    """Меню для менеджера"""
    keyboard = [
        [KeyboardButton(text="Добавить ученика"), KeyboardButton(text="Посещаемость")],
        [KeyboardButton(text="Оплаты"), KeyboardButton(text="Города")],
        [KeyboardButton(text="Отчёты"), KeyboardButton(text="Информация")],
        [KeyboardButton(text="Рассылка")],
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        input_field_placeholder="Выберите действие"
    )


def get_teacher_menu() -> ReplyKeyboardMarkup:
    """Меню для преподавателя"""
    keyboard = [
        [KeyboardButton(text="Добавить ученика"), KeyboardButton(text="Посещаемость")],
        [KeyboardButton(text="Оплаты"), KeyboardButton(text="Отчёты")],
        [KeyboardButton(text="Информация")],
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        input_field_placeholder="Выберите действие"
    )


def get_smm_menu() -> ReplyKeyboardMarkup:
    """Меню для SMM"""
    keyboard = [
        [KeyboardButton(text="Добавить ученика"), KeyboardButton(text="Свободные места")],
        [KeyboardButton(text="Отчет по привлеченным")],
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        input_field_placeholder="Выберите действие"
    )

