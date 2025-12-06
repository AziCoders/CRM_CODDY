"""Обработчик отчетов по оплатам для VK"""
from vkbottle.bot import BotLabeler, Message
from vk_bot.services.role_storage import RoleStorage
from vk_bot.services.payment_report_service import generate_report
import re

labeler = BotLabeler()
storage = RoleStorage()

MONTH_NAMES = [
    "январь", "февраль", "март", "апрель", "май", "июнь",
    "июль", "август", "сентябрь", "октябрь", "ноябрь", "декабрь"
]

def parse_payment_report_query(text: str):
    """
    Парсит запрос в формате "отчет по оплатам <город> <месяц>"
    Возвращает (город, месяц) или None
    
    Примеры:
    - "отчет по оплатам Назрань ноябрь" -> ("Назрань", "ноябрь")
    - "отчет по оплатам все ноябрь" -> ("все", "ноябрь")
    - "отчет по оплатам Назрань" -> ("Назрань", None)
    """
    text = text.strip().lower()
    
    # Проверяем что это запрос на отчет
    if not text.startswith("отчет по оплатам"):
        return None
    
    # Убираем префикс
    query = text[len("отчет по оплатам"):].strip()
    
    if not query:
        return None
    
    # Разбиваем на части
    parts = query.split()
    
    if len(parts) == 0:
        return None
    
    city = None
    month = None
    
    # Первая часть всегда город
    city = parts[0].capitalize()
    
    # Вторая часть (если есть) - месяц
    if len(parts) >= 2:
        potential_month = parts[1].lower()
        if potential_month in MONTH_NAMES:
            month = potential_month.capitalize()
    
    return (city, month)

@labeler.private_message()
async def handle_payment_report(message: Message):
    """Обработчик запросов отчетов по оплатам"""
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
    parsed = parse_payment_report_query(text)
    if not parsed:
        return
    
    city_name, month = parsed
    
    # Проверяем права доступа к городу
    role = user_data.get("role")
    if role == "teacher":
        user_city_name = user_data.get("city", "")
        if city_name.lower() != "все" and user_city_name != city_name:
            await message.answer(
                f"❌ У вас нет доступа к городу '{city_name}'. "
                f"Вы можете смотреть отчеты только для города '{user_city_name}'."
            )
            return
        
        # Если учитель запросил "все", ограничиваем его городом
        if city_name.lower() == "все":
            city_name = user_city_name
    
    # Генерируем отчет
    try:
        await message.answer("⏳ Формирую отчет...")
        report = generate_report(city_name, month)
        
        # VK имеет ограничение на длину сообщения (примерно 4096 символов)
        # Разбиваем длинные отчеты на части
        MAX_LENGTH = 4000
        
        if len(report) <= MAX_LENGTH:
            await message.answer(report)
        else:
            # Разбиваем отчет на части
            parts = []
            current_part = ""
            
            for line in report.split("\n"):
                if len(current_part) + len(line) + 1 > MAX_LENGTH:
                    parts.append(current_part)
                    current_part = line + "\n"
                else:
                    current_part += line + "\n"
            
            if current_part:
                parts.append(current_part)
            
            # Отправляем части
            for i, part in enumerate(parts, 1):
                header = f"📊 Отчет (часть {i}/{len(parts)})\n\n" if len(parts) > 1 else ""
                await message.answer(header + part)
    
    except Exception as e:
        await message.answer(f"❌ Ошибка при формировании отчета: {e}")
