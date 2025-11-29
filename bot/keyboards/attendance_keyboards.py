"""Клавиатуры для отметки посещаемости"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters.callback_data import CallbackData
from bot.config import CITIES
from typing import List, Dict


class AttendanceCityCallback(CallbackData, prefix="att_city"):
    """Callback для выбора города при отметке посещаемости"""
    city: str


class AttendanceGroupCallback(CallbackData, prefix="att_group"):
    """Callback для выбора группы при отметке посещаемости"""
    group_id: str


class AttendanceStudentCallback(CallbackData, prefix="att_student"):
    """Callback для изменения статуса ученика"""
    student_id: str


class AttendanceConfirmCallback(CallbackData, prefix="att_confirm"):
    """Callback для подтверждения посещаемости"""
    confirm: bool  # True = подтвердить, False = отмена


class AttendanceBackCallback(CallbackData, prefix="att_back"):
    """Callback для возврата к выбору города"""
    pass


def get_attendance_cities_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора города при отметке посещаемости"""
    keyboard = []
    # Создаем кнопки по 2 в ряд
    for i in range(0, len(CITIES), 2):
        row = []
        row.append(InlineKeyboardButton(
            text=CITIES[i],
            callback_data=AttendanceCityCallback(city=CITIES[i]).pack()
        ))
        if i + 1 < len(CITIES):
            row.append(InlineKeyboardButton(
                text=CITIES[i + 1],
                callback_data=AttendanceCityCallback(city=CITIES[i + 1]).pack()
            ))
        keyboard.append(row)
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_attendance_groups_keyboard(groups: List[Dict], show_back: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура для выбора группы при отметке посещаемости"""
    keyboard = []
    for group in groups:
        group_id = group.get("group_id")
        group_name = group.get("group_name", "Без названия")
        
        keyboard.append([InlineKeyboardButton(
            text=group_name,
            callback_data=AttendanceGroupCallback(group_id=group_id).pack()
        )])
    
    # Добавляем кнопку "Назад" если нужно
    if show_back:
        keyboard.append([InlineKeyboardButton(
            text="🔙 Назад",
            callback_data=AttendanceBackCallback().pack()
        )])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_students_keyboard(students: List[Dict], attendance_statuses: Dict[str, int]) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру с учениками и кнопками подтверждения/отмены
    
    Args:
        students: Список учеников [{"ID": "...", "ФИО": "..."}, ...]
        attendance_statuses: Словарь {student_id: status_index}, где status_index:
            0 = нет отметки
            1 = ✅ Присутствовал
            2 = ❌ Отсутствовал
            3 = 🟡 Опоздал
            4 = 🟣 Отсутствовал по причине
    """
    keyboard = []
    
    # Варианты отметок
    status_icons = ["", "✅", "❌", "🟡", "🟣"]
    
    # Создаем кнопки для каждого ученика
    for student in students:
        student_id = student.get("ID", "")
        fio = student.get("ФИО", "Без имени")
        
        # Получаем текущий статус
        status_index = attendance_statuses.get(student_id, 0)
        status_icon = status_icons[status_index]
        
        # Формируем текст кнопки
        button_text = f"{fio} {status_icon}".strip()
        
        keyboard.append([InlineKeyboardButton(
            text=button_text,
            callback_data=AttendanceStudentCallback(student_id=student_id).pack()
        )])
    
    # Кнопки подтверждения и отмены
    keyboard.append([
        InlineKeyboardButton(
            text="Подтвердить ✅",
            callback_data=AttendanceConfirmCallback(confirm=True).pack()
        ),
        InlineKeyboardButton(
            text="Отмена ❌",
            callback_data=AttendanceConfirmCallback(confirm=False).pack()
        )
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

