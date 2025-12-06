"""Обработчик запросов отчетов по оплатам через текстовые команды"""
from typing import Optional, Tuple
from aiogram import Router
from aiogram.types import Message, FSInputFile
from aiogram.fsm.context import FSMContext
from bot.services.role_storage import RoleStorage
from bot.services.report_payments import generate_payments_report

router = Router()
role_storage = RoleStorage()

MONTH_NAMES = [
    "январь", "февраль", "март", "апрель", "май", "июнь",
    "июль", "август", "сентябрь", "октябрь", "ноябрь", "декабрь"
]

def parse_payment_report_query(text: str) -> Optional[Tuple[str, Optional[str]]]:
    """
    Парсит запрос в формате "отчет по оплатам <город> <месяц>"
    Возвращает (город, месяц) или None
    
    Примеры:
    - "отчет по оплатам Назрань ноябрь" -> ("Назрань", "Ноябрь")
    - "отчет по оплатам все ноябрь" -> ("все", "Ноябрь")
    - "отчет по оплатам Назрань" -> ("Назрань", None)
    
    Примечание: месяц сейчас игнорируется, т.к. generate_payments_report
    всегда использует текущий месяц. Но парсим для будущего расширения.
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


@router.message()
async def handle_payment_report_query(message: Message, state: FSMContext, user_role: str = None, user_city: str = None):
    """Обработчик запросов отчетов по оплатам"""
    # Проверяем права доступа
    if user_role is None or user_role == "pending":
        return  # Не обрабатываем для незарегистрированных
    
    # Пропускаем, если пользователь в FSM состоянии
    current_state = await state.get_state()
    if current_state:
        return
    
    text = message.text.strip() if message.text else ""
    
    # Парсим запрос
    parsed = parse_payment_report_query(text)
    if not parsed:
        return  # Не наш формат, пропускаем
    
    city_name, month = parsed
    
    # Проверяем права доступа к городу
    if user_role == "teacher":
        user_data = role_storage.get_user(message.from_user.id)
        if user_data:
            user_city_name = user_data.get("city", "")
            # Если учитель запросил "все" или другой город, ограничиваем его городом
            if city_name.lower() == "все" or user_city_name != city_name:
                city_name = user_city_name
    
    # Генерируем отчет (используем тот же сервис что и кнопочные отчеты)
    try:
        await message.answer("⏳ Формирую отчет...")
        
        # generate_payments_report возвращает (summary_text, excel_path)
        summary_text, excel_path = generate_payments_report(city_name)
        
        # Отправляем текстовый отчет
        await message.answer(summary_text)
        
        # Отправляем Excel файл
        document = FSInputFile(excel_path)
        caption = f"📊 Отчет по оплатам: {city_name}"
        if city_name == "all":
            caption = "📊 Общий отчет по оплатам (все города)"
        
        await message.answer_document(
            document,
            caption=caption
        )
    
    except Exception as e:
        await message.answer(f"❌ Ошибка при формировании отчета: {e}")
        import traceback
        traceback.print_exc()

