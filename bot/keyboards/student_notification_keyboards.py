"""Клавиатуры для уведомлений о новых учениках"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters.callback_data import CallbackData


class StudentProcessedCallback(CallbackData, prefix="student_processed"):
    """Callback для обработки ученика"""
    student_id: str  # ID ученика в Notion
    notification_id: str  # Уникальный ID уведомления для группировки сообщений


def get_student_processed_keyboard(student_id: str, notification_id: str) -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой 'Обработали'"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="✅ Обработали",
            callback_data=StudentProcessedCallback(
                student_id=student_id,
                notification_id=notification_id
            ).pack()
        )]
    ])

