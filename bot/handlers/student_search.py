"""Обработчик поиска учеников"""
from typing import Optional, Tuple
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from bot.services.student_search import StudentSearchService
from bot.config import CITIES, CITY_MAPPING
from bot.services.role_storage import RoleStorage

router = Router()
search_service = StudentSearchService()
role_storage = RoleStorage()


def parse_search_query(text: str) -> Optional[Tuple[str, str]]:
    """
    Парсит запрос в формате "Город <запрос>"
    Возвращает (город, запрос) или None
    """
    text = text.strip()
    
    # Ищем город в начале строки
    for city in CITIES:
        if text.lower().startswith(city.lower()):
            query = text[len(city):].strip()
            if query:
                return (city, query)
    
    return None


def format_full_info(student: dict) -> str:
    """Форматирует полную информацию об ученике"""
    lines = [
        f"👤 <b>{student.get('ФИО', 'Не указано')}</b>",
        f"",
        f"📞 Номер родителя: {student.get('Номер родителя', 'Не указан')}",
        f"👨‍👩‍👧 Имя родителя: {student.get('Имя родителя', 'Не указано')}",
        f"🎂 Возраст: {student.get('Возраст', 'Не указан')}",
        f"📅 Дата поступления: {student.get('Дата поступления', 'Не указана')}",
        f"",
        f"🏫 Группа: {student.get('group_name', 'Не указана')}",
        f"💰 Тариф: {student.get('Тариф', 'Не указан')}",
        f"📊 Статус: {student.get('Статус', 'Не указан')}",
        f"🏙️ Город: {student.get('Город', 'Не указан')}",
    ]
    
    if student.get('Комментарии'):
        lines.append(f"💬 Комментарий: {student.get('Комментарии')}")
    
    if student.get('Ссылка на WA, TG'):
        lines.append(f"🔗 Ссылка: {student.get('Ссылка на WA, TG')}")
    
    if student.get('student_url'):
        lines.append(f"")
        lines.append(f"🔗 Notion: {student.get('student_url')}")
    
    return "\n".join(lines)


def format_list(students: list[dict]) -> str:
    """Форматирует список учеников (краткая информация)"""
    if not students:
        return "❌ Ничего не найдено"
    
    lines = [f"📋 Найдено учеников: {len(students)}\n"]
    
    for i, student in enumerate(students, 1):
        fio = student.get('ФИО', 'Не указано')
        phone = student.get('Номер родителя', 'Не указан')
        group = student.get('group_name', 'Не указана')
        
        lines.append(f"{i}. <b>{fio}</b>")
        lines.append(f"   📞 {phone}")
        lines.append(f"   🏫 {group}")
        lines.append("")
    
    return "\n".join(lines)


@router.message(F.text & ~F.text.startswith("/"))
async def handle_search(message: Message, state: FSMContext, user_role: str = None, user_city: str = None):
    """Обработчик поиска учеников"""
    # Проверяем права доступа
    if user_role is None or user_role == "pending":
        return  # Не обрабатываем для незарегистрированных
    
    # Пропускаем, если пользователь в FSM состоянии добавления ученика
    current_state = await state.get_state()
    if current_state and "AddStudentState" in str(current_state):
        return  # Пропускаем, если пользователь добавляет ученика
    
    # Пропускаем кнопки меню
    menu_buttons = ["Добавить ученика", "Посещаемость", "Города", "Оплаты", 
                    "Синхронизация", "Отчёты", "ИИ-отчёт", "Свободные места",
                    "Управление ролями", "Отмена"]
    if message.text in menu_buttons:
        return
    
    text = message.text.strip() if message.text else ""
    
    # Парсим запрос
    parsed = parse_search_query(text)
    if not parsed:
        return  # Не наш формат, пропускаем
    
    city_name, query = parsed
    
    # Проверяем права доступа к городу
    if user_role == "teacher":
        # Преподаватель может искать только в своем городе
        user_data = role_storage.get_user(message.from_user.id)
        if user_data:
            user_city_name = user_data.get("city", "")
            if user_city_name != city_name:
                await message.answer(
                    f"❌ У вас нет доступа к городу '{city_name}'. "
                    f"Вы можете искать только в городе '{user_city_name}'."
                )
                return
    
    # Выполняем поиск
    try:
        result_type, data = search_service.search(city_name, query)
        
        if result_type == "not_found":
            await message.answer(
                f"❌ Ученик не найден в городе '{city_name}' по запросу: {query}"
            )
        elif result_type == "full_info":
            formatted = format_full_info(data)
            await message.answer(formatted, parse_mode="HTML")
        elif result_type == "list":
            formatted = format_list(data)
            await message.answer(formatted, parse_mode="HTML")
    
    except Exception as e:
        await message.answer(
            f"❌ Произошла ошибка при поиске: {str(e)}"
        )
        print(f"Ошибка поиска: {e}")

