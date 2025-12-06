"""Клавиатуры для уведомлений о новых учениках"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters.callback_data import CallbackData


class StudentProcessedCallback(CallbackData, prefix="student_processed"):
    """Callback для обработки ученика"""
    notif: str


def get_student_processed_keyboard(notification_id: str):
    short_id = notification_id[:8]

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✔ Обработано",
                    callback_data=StudentProcessedCallback(notif=short_id).pack()
                )
            ]
        ]
    )


