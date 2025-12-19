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
    Парсит запрос в формате "Город <запрос>" или "ПОИСК <запрос>"
    Возвращает (город, запрос) или None
    Если начинается с "ПОИСК", возвращает (None, запрос) для поиска по всем городам
    """
    text = text.strip()
    
    # Проверяем формат "ПОИСК <запрос>"
    if text.upper().startswith("ПОИСК"):
        query = text[5:].strip()  # Убираем "ПОИСК" и пробелы
        if query:
            return (None, query)  # None означает поиск по всем городам
    
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


def format_list(students: list[dict], include_phone: bool = True, all_cities: bool = False) -> str:
    """Форматирует список учеников (краткая информация)"""
    if not students:
        return "❌ Ничего не найдено"
    
    lines = [f"📋 Найдено учеников: {len(students)}\n"]
    
    for i, student in enumerate(students, 1):
        fio = student.get('ФИО', 'Не указано')
        city = student.get('Город', '')
        phone = student.get('Номер родителя', 'Не указан')
        group = student.get('group_name', 'Не указана')
        
        if all_cities and city:
            # Формат для поиска по всем городам: <Город> <ФИО> <НОМЕР> <Группа>
            if include_phone:
                lines.append(
                    f"{i}. <code>{city} {fio}</code> {phone} <b>{group}</b>"
                )
            else:
                # Для преподов: <Город> <ФИО>
                lines.append(f"{i}. <code>{city} {fio}</code>")
        else:
            # Старый формат для поиска по одному городу
            lines.append(f"{i}. <code>{fio}</code>")
            if include_phone:
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
    
    # Если city_name == None, значит поиск по всем городам (формат "ПОИСК <query>")
    if city_name is None:
        # Поиск по всем городам
        user_data = role_storage.get_user(message.from_user.id)
        user_city = None
        
        # Для преподавателей ограничиваем поиск только своим городом
        if user_role == "teacher":
            if user_data:
                user_city = user_data.get("city", "")
                if not user_city:
                    await message.answer("❌ Не указан ваш город для поиска")
                    return
        
        # Выполняем поиск по всем городам (или только по городу преподавателя)
        try:
            results = search_service.search_all_cities(query, user_city=user_city)
            
            if not results:
                if user_role == "teacher":
                    await message.answer(
                        f"❌ Ученик не найден в городе '{user_city}' по запросу: {query}"
                    )
                else:
                    await message.answer(
                        f"❌ Ученик не найден ни в одном городе по запросу: {query}"
                    )
            else:
                # Если найден один ученик - показываем профиль с кнопками
                if len(results) == 1:
                    student = results[0]
                    formatted = format_full_info(student)
                    from bot.keyboards.student_profile_keyboards import get_student_profile_keyboard
                    student_id = student.get("ID", "")
                    city = student.get("Город", "")
                    group_id = student.get("group_id", "")
                    keyboard = get_student_profile_keyboard(student_id, city, group_id)
                    await message.answer(formatted, parse_mode="HTML", reply_markup=keyboard)
                else:
                    # Форматируем результаты
                    if user_role == "teacher":
                        # Для преподов: <Город> <ФИО>
                        formatted = format_list(results, include_phone=False, all_cities=True)
                    else:
                        # Для остальных: <Город> <ФИО> <НОМЕР> <Группа>
                        formatted = format_list(results, include_phone=True, all_cities=True)
                    await message.answer(formatted, parse_mode="HTML")
        
        except Exception as e:
            await message.answer(
                f"❌ Произошла ошибка при поиске: {str(e)}"
            )
            print(f"Ошибка поиска: {e}")
        return
    
    # Старая логика поиска по одному городу ("Город <query>")
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
            # Добавляем кнопки Оплата и Удалить
            from bot.keyboards.student_profile_keyboards import get_student_profile_keyboard
            student_id = data.get("ID", "")
            group_id = data.get("group_id", "")
            keyboard = get_student_profile_keyboard(student_id, city_name, group_id)
            await message.answer(formatted, parse_mode="HTML", reply_markup=keyboard)
        elif result_type == "list":
            formatted = format_list(data, include_phone=True, all_cities=False)
            await message.answer(formatted, parse_mode="HTML")
    
    except Exception as e:
        await message.answer(
            f"❌ Произошла ошибка при поиске: {str(e)}"
        )
        print(f"Ошибка поиска: {e}")

