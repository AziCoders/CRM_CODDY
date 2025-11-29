"""Клавиатуры для отметки оплаты"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters.callback_data import CallbackData
from bot.config import CITIES
from typing import List, Dict


class PaymentStatusCallback(CallbackData, prefix="payment_status"):
    """Callback для выбора статуса оплаты"""
    status: str  # Оплатил, Написали, Не оплатил, Отсрочка


class PaymentBackCallback(CallbackData, prefix="payment_back"):
    """Callback для возврата"""
    pass


class PaymentCityCallback(CallbackData, prefix="pay_city"):
    """Callback для выбора города при оплате"""
    city: str


class PaymentStudentCallback(CallbackData, prefix="pay_student"):
    """Callback для выбора ученика"""
    student_id: str


class PaymentPaginationCallback(CallbackData, prefix="pay_page"):
    """Callback для пагинации списка учеников"""
    city: str
    page: int  # Номер страницы (начинается с 0)


class PaymentAddCommentCallback(CallbackData, prefix="pay_comment"):
    """Callback для добавления комментария"""
    pass


def get_payment_cities_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора города при оплате"""
    keyboard = []
    # Создаем кнопки по 2 в ряд
    for i in range(0, len(CITIES), 2):
        row = []
        row.append(InlineKeyboardButton(
            text=CITIES[i],
            callback_data=PaymentCityCallback(city=CITIES[i]).pack()
        ))
        if i + 1 < len(CITIES):
            row.append(InlineKeyboardButton(
                text=CITIES[i + 1],
                callback_data=PaymentCityCallback(city=CITIES[i + 1]).pack()
            ))
        keyboard.append(row)
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_payment_status_icon(status: str) -> str:
    """Возвращает иконку для статуса оплаты"""
    status_icons = {
        "Оплатил": "✅",
        "Написали": "🖌",
        "Не оплатил": "❌",
        "Отсрочка": "⏳"
    }
    return status_icons.get(status, "")


def get_payment_students_keyboard(
    students: List[Dict], 
    city: str, 
    page: int, 
    total_pages: int,
    payment_statuses: Dict[str, str] = None
) -> InlineKeyboardMarkup:
    """
    Клавиатура для выбора ученика с пагинацией (по 10 на страницу)
    
    Args:
        students: Список учеников
        city: Название города
        page: Текущая страница
        total_pages: Всего страниц
        payment_statuses: Словарь {student_id: status} для отображения статусов
    """
    keyboard = []
    
    # Показываем учеников текущей страницы
    for student in students:
        fio = student.get("ФИО", "Без имени")
        student_id = student.get("ID", "")
        
        # Получаем статус оплаты для ученика
        status_icon = ""
        if payment_statuses:
            status = payment_statuses.get(student_id, "")
            status_icon = get_payment_status_icon(status)
        
        # Формируем текст кнопки с иконкой статуса
        button_text = f"{fio} {status_icon}".strip()
        
        keyboard.append([InlineKeyboardButton(
            text=button_text,
            callback_data=PaymentStudentCallback(student_id=student_id).pack()
        )])
    
    # Кнопки пагинации
    pagination_row = []
    if page > 0:
        pagination_row.append(InlineKeyboardButton(
            text="◀️ Назад",
            callback_data=PaymentPaginationCallback(city=city, page=page - 1).pack()
        ))
    
    if page < total_pages - 1:
        pagination_row.append(InlineKeyboardButton(
            text="Вперед ▶️",
            callback_data=PaymentPaginationCallback(city=city, page=page + 1).pack()
        ))
    
    if pagination_row:
        keyboard.append(pagination_row)
    
    # Кнопка "Назад" к выбору города
    keyboard.append([InlineKeyboardButton(
        text="🔙 Назад",
        callback_data=PaymentBackCallback().pack()
    )])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_payment_status_keyboard(show_add_comment: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура для выбора статуса оплаты"""
    keyboard = [
        [
            InlineKeyboardButton(
                text="Оплатил ✅",
                callback_data=PaymentStatusCallback(status="Оплатил").pack()
            ),
            InlineKeyboardButton(
                text="Написали 🖌",
                callback_data=PaymentStatusCallback(status="Написали").pack()
            )
        ],
        [
            InlineKeyboardButton(
                text="Не оплатил ❌",
                callback_data=PaymentStatusCallback(status="Не оплатил").pack()
            ),
            InlineKeyboardButton(
                text="Отсрочка ⏳",
                callback_data=PaymentStatusCallback(status="Отсрочка").pack()
            )
        ]
    ]
    
    # Добавляем кнопку "Добавить комментарий" если нужно
    if show_add_comment:
        keyboard.append([InlineKeyboardButton(
            text="Добавить комментарий",
            callback_data=PaymentAddCommentCallback().pack()
        )])
    
    keyboard.append([InlineKeyboardButton(
        text="Отмена ❌",
        callback_data=PaymentBackCallback().pack()
    )])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_only_comment_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура только с кнопкой добавления комментария"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="Добавить комментарий 💬",
            callback_data=PaymentAddCommentCallback().pack()
        )]
    ])