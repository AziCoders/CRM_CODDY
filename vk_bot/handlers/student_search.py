"""Обработчик поиска учеников для VK"""
from vkbottle.bot import BotLabeler, Message
from vk_bot.services.role_storage import RoleStorage
from bot.services.student_search import StudentSearchService
from bot.config import CITIES

labeler = BotLabeler()
storage = RoleStorage()
search_service = StudentSearchService()

def parse_search_query(text: str):
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
        f"👤 {student.get('ФИО', 'Не указано')}",
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
        
        lines.append(f"{i}. <code>{fio}</code>")
        lines.append(f"   📞 {phone}")
        lines.append(f"   🏫 {group}")
        lines.append("")
    
    return "\n".join(lines)

@labeler.private_message()
async def handle_search(message: Message):
    """Обработчик поиска учеников"""
    user_id = message.from_id
    
    # Проверяем роль
    user_data = storage.get_user(user_id)
    if not user_data or user_data.get("role") == "pending":
        return

    text = message.text
    
    # Пропускаем команды
    if text.startswith("/"):
        return

    # Парсим запрос
    parsed = parse_search_query(text)
    if not parsed:
        return
    
    city_name, query = parsed
    
    # Проверяем права доступа к городу
    role = user_data.get("role")
    if role == "teacher":
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
            await message.answer(formatted)
        elif result_type == "list":
            formatted = format_list(data)
            await message.answer(formatted)
    
    except Exception as e:
        await message.answer(f"❌ Ошибка при поиске: {e}")
