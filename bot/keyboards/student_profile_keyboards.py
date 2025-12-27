"""Клавиатуры для профиля ученика"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters.callback_data import CallbackData


class StudentPaymentCallback(CallbackData, prefix="sp"):
    """Callback для оплаты ученика из профиля"""
    student_id: str
    city_en: str  # Используем английское название города для экономии места


class StudentDeleteCallback(CallbackData, prefix="sd"):
    """Callback для удаления ученика из профиля"""
    student_id: str
    city_en: str  # Используем английское название города для экономии места
    group_id: str = ""


class CancelDeleteCallback(CallbackData, prefix="cancel_delete"):
    """Callback для отмены удаления ученика"""
    pass


class StudentAttendanceCallback(CallbackData, prefix="sa"):
    """Callback для просмотра посещаемости ученика"""
    student_id: str
    city_en: str


class BackToStudentsCallback(CallbackData, prefix="bts"):
    """Callback для возврата к списку учеников группы"""
    group_id: str  # Сокращенный ID группы (первые 16 символов)
    city_en: str  # Английское название города (сокращенное до 6 символов)


def get_student_profile_keyboard(student_id: str, city: str, group_id: str = "", show_back: bool = False, user_role: str = None) -> InlineKeyboardMarkup:
    """
    Клавиатура с кнопками Оплата, Удалить и Просмотр посещаемости для профиля ученика
    
    Args:
        student_id: ID ученика
        city: Название города
        group_id: ID группы (опционально)
        show_back: Показывать ли кнопку "Назад" (только если профиль получен через кнопки)
        user_role: Роль пользователя (owner, manager, teacher, smm, pending)
    
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками в зависимости от роли пользователя
        - Для SMM: пустая клавиатура (без кнопок)
        - Для teacher: кнопки Оплата и Просмотр посещаемости (без Удалить)
        - Для owner и manager: все кнопки (Оплата, Удалить, Просмотр посещаемости)
    """
    # Для SMM и pending не показываем кнопки действий (только "Назад", если нужно)
    if user_role in ["smm", "pending"] or user_role is None:
        keyboard = []
        # Если есть кнопка "Назад", все равно показываем её
        if show_back and group_id:
            from bot.config import CITY_MAPPING
            city_en = CITY_MAPPING.get(city, city)[:6]
            group_id_short = group_id.replace("-", "")[:16] if group_id else ""
            keyboard.append([
                InlineKeyboardButton(
                    text="◀️ Назад",
                    callback_data=BackToStudentsCallback(group_id=group_id_short, city_en=city_en).pack()
                )
            ])
        return InlineKeyboardMarkup(inline_keyboard=keyboard) if keyboard else None
    
    from bot.config import CITY_MAPPING
    # Используем английское название города для callback_data, сокращаем до 6 символов
    city_en = CITY_MAPPING.get(city, city)[:6]
    
    # Убираем дефисы из UUID и сокращаем до 16 символов для экономии места
    # Первые 16 символов UUID обычно достаточно уникальны
    student_id_short = student_id.replace("-", "")[:16] if student_id else ""
    group_id_short = group_id.replace("-", "")[:16] if group_id else ""
    
    keyboard = []
    
    # Кнопка "Оплата" - доступна для owner, manager, teacher
    payment_button = InlineKeyboardButton(
        text="💰 Оплата",
        callback_data=StudentPaymentCallback(student_id=student_id_short, city_en=city_en).pack()
    )
    
    # Кнопка "Удалить" - только для owner и manager
    delete_button = InlineKeyboardButton(
        text="🗑️ Удалить",
        callback_data=StudentDeleteCallback(student_id=student_id_short, city_en=city_en, group_id=group_id_short).pack()
    )
    
    # Кнопка "Просмотр посещаемости" - доступна для owner, manager, teacher
    attendance_button = InlineKeyboardButton(
        text="📊 Просмотр посещаемости",
        callback_data=StudentAttendanceCallback(student_id=student_id_short, city_en=city_en).pack()
    )
    
    # Формируем кнопки в зависимости от роли
    if user_role in ["owner", "manager"]:
        # Для owner и manager показываем все кнопки
        keyboard.append([payment_button, delete_button])
        keyboard.append([attendance_button])
    elif user_role == "teacher":
        # Для teacher не показываем кнопку "Удалить"
        keyboard.append([payment_button])
        keyboard.append([attendance_button])
    
    # Добавляем кнопку "Назад" только если профиль получен через кнопки
    if show_back and group_id_short:
        keyboard.append([
            InlineKeyboardButton(
                text="◀️ Назад",
                callback_data=BackToStudentsCallback(group_id=group_id_short, city_en=city_en).pack()
            )
        ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard) if keyboard else None


def get_cancel_delete_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура только с кнопкой отмены удаления"""
    keyboard = [[InlineKeyboardButton(
        text="❌ Отмена",
        callback_data=CancelDeleteCallback().pack()
    )]]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

