"""Клавиатуры для навигации по информации"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters.callback_data import CallbackData
from typing import List, Dict


class InfoMenuCallback(CallbackData, prefix="info_menu"):
    """Callback для главного меню информации"""
    city: str = ""  # Пустая строка означает выбор города


class CityInfoCallback(CallbackData, prefix="city_info"):
    """Callback для выбора города в информации"""
    city: str


class InfoActionCallback(CallbackData, prefix="ia"):
    """Callback для действий в информации (информация, группы)"""
    action: str  # "info" или "groups"
    city_en: str  # Английское название города (сокращенное до 6 символов)


class GroupInfoCallback(CallbackData, prefix="gi"):
    """Callback для выбора группы"""
    group_id: str  # Сокращенный ID (первые 16 символов без дефисов)
    city_en: str  # Английское название города (сокращенное до 6 символов)


class GroupStudentsCallback(CallbackData, prefix="gs"):
    """Callback для просмотра учеников группы"""
    group_id: str  # Сокращенный ID (первые 16 символов без дефисов)
    city_en: str  # Английское название города (сокращенное до 6 символов)


class StudentSelectCallback(CallbackData, prefix="ss"):
    """Callback для выбора ученика из группы"""
    student_id: str  # Сокращенный ID (первые 16 символов без дефисов)
    city_en: str  # Английское название города (сокращенное до 6 символов)
    group_id: str  # Сокращенный ID (первые 10 символов без дефисов)


class BackCallback(CallbackData, prefix="back"):
    """Callback для кнопки Назад"""
    level: str  # "main", "city", "groups", "group", "students"
    city_en: str = ""  # Английское название города (сокращенное до 6 символов)
    group_id: str = ""  # Сокращенный ID (первые 10 символов без дефисов)


def get_info_cities_keyboard(cities: List[str]) -> InlineKeyboardMarkup:
    """Клавиатура для выбора города в информации"""
    keyboard = []
    for city in cities:
        keyboard.append([
            InlineKeyboardButton(
                text=city,
                callback_data=CityInfoCallback(city=city).pack()
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_info_menu_keyboard(city: str) -> InlineKeyboardMarkup:
    """Клавиатура главного меню информации для города"""
    from bot.config import CITY_MAPPING
    
    # Сокращаем данные для callback
    city_en = CITY_MAPPING.get(city, city)[:6]
    
    keyboard = [
        [
            InlineKeyboardButton(
                text="📋 Информация",
                callback_data=InfoActionCallback(action="info", city_en=city_en).pack()
            ),
            InlineKeyboardButton(
                text="👥 Группы",
                callback_data=InfoActionCallback(action="groups", city_en=city_en).pack()
            )
        ],
        [
            InlineKeyboardButton(
                text="◀️ Назад",
                callback_data=BackCallback(level="main").pack()
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_groups_list_keyboard(groups: List[Dict], city: str) -> InlineKeyboardMarkup:
    """Клавиатура со списком групп"""
    from bot.config import CITY_MAPPING
    
    # Сокращаем данные для callback
    city_en = CITY_MAPPING.get(city, city)[:6]
    
    keyboard = []
    for group in groups:
        group_name = group.get("group_name", "Без названия")
        group_id_full = group.get("group_id", "")
        # Сокращаем group_id до 16 символов без дефисов
        group_id_short = group_id_full.replace("-", "")[:16] if group_id_full else ""
        
        keyboard.append([
            InlineKeyboardButton(
                text=group_name,
                callback_data=GroupInfoCallback(group_id=group_id_short, city_en=city_en).pack()
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton(
            text="◀️ Назад",
            callback_data=BackCallback(level="city", city_en=city_en).pack()
        )
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_group_info_keyboard(group_id: str, city: str) -> InlineKeyboardMarkup:
    """Клавиатура для информации о группе"""
    from bot.config import CITY_MAPPING
    
    # Сокращаем данные для callback
    city_en = CITY_MAPPING.get(city, city)[:6]
    group_id_short = group_id.replace("-", "")[:16] if group_id else ""
    
    keyboard = [
        [
            InlineKeyboardButton(
                text="👥 Ученики",
                callback_data=GroupStudentsCallback(group_id=group_id_short, city_en=city_en).pack()
            ),
            InlineKeyboardButton(
                text="📜 Сформировать сертификаты",
                callback_data="certificates_not_implemented"  # Пока не реализовано
            )
        ],
        [
            InlineKeyboardButton(
                text="◀️ Назад",
                callback_data=BackCallback(level="groups", city_en=city_en).pack()
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_students_list_keyboard(students: List[Dict], group_id: str, city: str) -> InlineKeyboardMarkup:
    """Клавиатура со списком учеников группы"""
    from bot.config import CITY_MAPPING
    
    # Сокращаем данные для callback
    city_en = CITY_MAPPING.get(city, city)[:6]
    group_id_short = group_id.replace("-", "")[:10] if group_id else ""
    
    # Отладочная информация
    print(f"🔘 Создаю клавиатуру учеников: group_id_full={group_id}, group_id_short={group_id_short}, students_count={len(students)}")
    
    keyboard = []
    for student in students:
        student_name = student.get("ФИО", "Без имени")
        student_id_full = student.get("ID", "")
        # Сокращаем ID до 16 символов без дефисов
        student_id_short = student_id_full.replace("-", "")[:16] if student_id_full else ""
        
        if not student_id_short:
            print(f"⚠️ Ученик {student_name} не имеет ID для создания кнопки")
            continue
        
        # Сокращаем имя если слишком длинное
        if len(student_name) > 30:
            student_name = student_name[:27] + "..."
        
        # Отладочная информация
        print(f"🔘 Создаю кнопку для ученика: {student_name[:30]}, ID_full={student_id_full}, ID_short={student_id_short}, group_id_short={group_id_short}")
        
        keyboard.append([
            InlineKeyboardButton(
                text=student_name,
                callback_data=StudentSelectCallback(
                    student_id=student_id_short,
                    city_en=city_en,
                    group_id=group_id_short
                ).pack()
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton(
            text="◀️ Назад",
            callback_data=BackCallback(level="group", city_en=city_en, group_id=group_id_short).pack()
        )
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_back_to_info_keyboard(city: str) -> InlineKeyboardMarkup:
    """Клавиатура только с кнопкой Назад к информации"""
    from bot.config import CITY_MAPPING
    
    # Сокращаем данные для callback
    city_en = CITY_MAPPING.get(city, city)[:6]
    
    keyboard = [[
        InlineKeyboardButton(
            text="◀️ Назад",
            callback_data=BackCallback(level="city", city_en=city_en).pack()
        )
    ]]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
