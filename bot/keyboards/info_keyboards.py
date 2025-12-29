"""Клавиатуры для навигации по информации"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters.callback_data import CallbackData
from typing import List, Dict
from bot.services.id_mapping import id_mapping_service


def _get_city_en(city: str) -> str:
    """Получает полное английское название города из маппинга"""
    from bot.config import CITY_MAPPING
    return CITY_MAPPING.get(city, city)


def _shorten_uuid(uuid_str: str, length: int = 8) -> str:
    """Сокращает UUID до указанной длины (убирает дефисы и берет первые символы)"""
    if not uuid_str:
        return ""
    # Убираем дефисы, приводим к нижнему регистру и берем первые символы
    uuid_no_dashes = uuid_str.replace("-", "").lower().strip()
    return uuid_no_dashes[:length]


def _shorten_city(city_en: str, length: int = 2) -> str:
    """Сокращает название города до указанной длины"""
    if not city_en:
        return ""
    return city_en[:length]


class InfoMenuCallback(CallbackData, prefix="info_menu"):
    """Callback для главного меню информации"""
    city: str = ""  # Пустая строка означает выбор города


class CityInfoCallback(CallbackData, prefix="city_info"):
    """Callback для выбора города в информации"""
    city: str


class InfoActionCallback(CallbackData, prefix="ia"):
    """Callback для действий в информации (информация, группы)"""
    action: str  # "info" или "groups"
    city_en: str  # Полное английское название города


class GroupInfoCallback(CallbackData, prefix="gi"):
    """Callback для выбора группы"""
    group_id: str  # Полный ID группы (UUID)
    city_en: str  # Полное английское название города


class GroupStudentsCallback(CallbackData, prefix="gs"):
    """Callback для просмотра учеников группы"""
    group_id: str  # Полный ID группы (UUID)
    city_en: str  # Полное английское название города


class StudentSelectCallback(CallbackData, prefix="ss"):
    """Callback для выбора ученика из группы"""
    student_id: str  # Короткий ID ученика (2 цифры)
    city_en: str  # Сокращенное английское название города (первые 2 символа)
    group_id: str  # Короткий ID группы (2 цифры)


class BackCallback(CallbackData, prefix="back"):
    """Callback для кнопки Назад"""
    level: str  # "main", "city", "groups", "group", "students"
    city_en: str = ""  # Полное английское название города (обязательно для level != "main")
    group_id: str = ""  # Полный ID группы (обязательно для level == "group" или "students")


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
    city_en = _get_city_en(city)
    
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
    city_en = _get_city_en(city)
    
    keyboard = []
    for group in groups:
        group_name = group.get("group_name", "Без названия")
        group_id = group.get("group_id", "")
        
        if not group_id:
            continue
        
        keyboard.append([
            InlineKeyboardButton(
                text=group_name,
                callback_data=GroupInfoCallback(group_id=group_id, city_en=city_en).pack()
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
    city_en = _get_city_en(city)
    
    keyboard = [
        [
            InlineKeyboardButton(
                text="👥 Ученики",
                callback_data=GroupStudentsCallback(group_id=group_id, city_en=city_en).pack()
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
    city_en = _get_city_en(city)
    
    # Создаем маппинг для группы
    group_id_short = id_mapping_service.add_mapping("group", group_id)
    
    keyboard = []
    for idx, student in enumerate(students):
        student_name = student.get("ФИО", "Без имени")
        student_id = student.get("ID", "")
        
        if not student_id:
            print(f"⚠️ Ученик #{idx+1} '{student_name}' не имеет ID, пропускаем")
            continue
        
        # Сокращаем имя если слишком длинное
        if len(student_name) > 30:
            student_name = student_name[:27] + "..."
        
        # Создаем маппинг для ученика
        student_id_short = id_mapping_service.add_mapping("student", student_id)
        city_en_short = _shorten_city(city_en, 2)
        
        keyboard.append([
            InlineKeyboardButton(
                text=student_name,
                callback_data=StudentSelectCallback(
                    student_id=student_id_short,
                    city_en=city_en_short,
                    group_id=group_id_short
                ).pack()
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton(
            text="◀️ Назад",
            callback_data=BackCallback(level="group", city_en=city_en, group_id=group_id).pack()
        )
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_back_to_info_keyboard(city: str) -> InlineKeyboardMarkup:
    """Клавиатура только с кнопкой Назад к информации"""
    city_en = _get_city_en(city)
    
    keyboard = [[
        InlineKeyboardButton(
            text="◀️ Назад",
            callback_data=BackCallback(level="city", city_en=city_en).pack()
        )
    ]]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
