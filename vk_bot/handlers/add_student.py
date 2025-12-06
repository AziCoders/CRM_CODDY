"""Обработчик добавления ученика для VK"""
import re
from vkbottle.bot import BotLabeler, Message, rules
from vkbottle import BaseStateGroup, CtxStorage
from vk_bot.services.role_storage import RoleStorage
from vk_bot.keyboards.add_student_keyboards import get_cities_keyboard, get_groups_keyboard, get_cancel_keyboard
from bot.services.group_service import GroupService
from bot.services.action_logger import ActionLogger
from bot.config import CITY_MAPPING
from src.CRUD.crud_student import NotionStudentCRUD

labeler = BotLabeler()
storage = RoleStorage()
group_service = GroupService()
action_logger = ActionLogger()
ctx_storage = CtxStorage()

class AddStudentState(BaseStateGroup):
    WAITING_CITY = "waiting_city"
    WAITING_GROUP = "waiting_group"
    WAITING_DATA = "waiting_data"

def get_template_message() -> str:
    """Возвращает шаблон для ввода данных"""
    return ("📝 Введите данные ученика в следующем формате:\n\n"
            "\"ФИО\": Иванов Иван Иванович,\n"
            "\"Возраст\": 10,\n"
            "\"Дата поступления\": \"2023-10-25\",\n"
            "\"Номер родителя\": +79001234567,\n"
            "\"Имя родителя\": Мария,\n"
            "\"Тариф\": \"Группа 2 раза\",\n"
            "\"Статус\": \"Обучается\",\n"
            "\"Ссылка на WA, TG\": \"\",\n"
            "\"Комментарий\": \"\""
            "\n\n"
            "⚠️ Обязательные поля: ФИО, Возраст, Номер родителя"
            )

def parse_student_data(text: str) -> dict:
    """Парсит данные ученика из текста"""
    data = {}
    text = text.strip()
    pattern = r'"([^"]+)":\s*"([^"]*)"|"([^"]+)":\s*([^,\n]+)'
    matches = re.findall(pattern, text, re.MULTILINE)

    for match in matches:
        if match[0]:
            key = match[0].strip()
            value = match[1].strip()
        else:
            key = match[2].strip()
            value = match[3].strip()

        if key == "Возраст":
            try:
                data[key] = int(value)
            except ValueError:
                data[key] = value
        else:
            data[key] = value
    return data

def validate_student_data(data: dict) -> tuple:
    """Валидирует данные ученика"""
    if not data.get("ФИО"):
        return False, "❌ Поле 'ФИО' обязательно"
    if not data.get("Возраст"):
        return False, "❌ Поле 'Возраст' обязательно"
    if not data.get("Номер родителя"):
        return False, "❌ Поле 'Номер родителя' обязательно"
    return True, ""

def prepare_student_data(data: dict, city_name: str) -> dict:
    """Подготавливает данные"""
    return {
        "ФИО": data.get("ФИО", ""),
        "Возраст": int(data.get("Возраст", 0)),
        "Дата поступления": data.get("Дата поступления", ""),
        "Номер родителя": data.get("Номер родителя", ""),
        "Имя родителя": data.get("Имя родителя", ""),
        "Тариф": data.get("Тариф", "Группа 2 раза"),
        "Статус": data.get("Статус", "Обучается"),
        "Город": city_name,
        "Ссылка на WA, TG": data.get("Ссылка на WA, TG", ""),
        "Комментарий": data.get("Комментарий", ""),
    }

@labeler.private_message(text="Добавить ученика")
async def start_add_student(message: Message):
    user_id = message.from_id
    user_data = storage.get_user(user_id)
    
    if not user_data or user_data.get("role") == "pending":
        await message.answer("❌ У вас нет доступа.")
        return

    role = user_data.get("role")
    if role == "teacher":
        city = user_data.get("city", "")
        ctx_storage.set(user_id, {"selected_city": city})
        await message.answer(
            f"🏙️ Город: {city}\nВыберите группу:",
            keyboard=get_groups_keyboard(group_service.get_city_groups(city))
        )
        await labeler.state_dispenser.set(user_id, AddStudentState.WAITING_GROUP)
    else:
        await message.answer("🏙️ Выберите город:", keyboard=get_cities_keyboard())
        await labeler.state_dispenser.set(user_id, AddStudentState.WAITING_CITY)

@labeler.private_message(state=AddStudentState.WAITING_CITY)
async def process_city_selection(message: Message):
    # Обработка выбора города (через payload или текст, если кнопки inline)
    # В VK inline кнопки отправляют payload, но событие message может не сработать если это callback
    # vkbottle обрабатывает callback отдельно, но мы можем использовать message event с payload rule
    pass 

@labeler.raw_event(rules.PayloadRule({"cmd": "select_city"}), dataclass=Message)
async def city_selected(message: Message):
    user_id = message.from_id
    payload = message.get_payload_json()
    city = payload["city"]
    
    ctx_storage.set(user_id, {"selected_city": city})
    
    groups = group_service.get_city_groups(city)
    if not groups:
        await message.answer(f"❌ Группы не найдены для города {city}")
        await labeler.state_dispenser.delete(user_id)
        return

    await message.answer(
        f"🏙️ Город: {city}\nВыберите группу:",
        keyboard=get_groups_keyboard(groups)
    )
    await labeler.state_dispenser.set(user_id, AddStudentState.WAITING_GROUP)

@labeler.raw_event(rules.PayloadRule({"cmd": "select_group"}), dataclass=Message)
async def group_selected(message: Message):
    user_id = message.from_id
    payload = message.get_payload_json()
    group_id = payload["group_id"]
    
    data = ctx_storage.get(user_id) or {}
    data["selected_group_id"] = group_id
    ctx_storage.set(user_id, data)
    
    await message.answer(
        f"{get_template_message()}\n\n💡 Напишите 'Отмена' для отмены.",
        keyboard=get_cancel_keyboard()
    )
    await labeler.state_dispenser.set(user_id, AddStudentState.WAITING_DATA)

@labeler.raw_event(rules.PayloadRule({"cmd": "cancel"}), dataclass=Message)
async def cancel_handler(message: Message):
    user_id = message.from_id
    await labeler.state_dispenser.delete(user_id)
    ctx_storage.delete(user_id)
    await message.answer("❌ Отменено")

@labeler.private_message(state=AddStudentState.WAITING_DATA)
async def process_data(message: Message):
    user_id = message.from_id
    text = message.text
    
    if text.lower() == "отмена":
        await labeler.state_dispenser.delete(user_id)
        ctx_storage.delete(user_id)
        await message.answer("❌ Отменено")
        return

    data = ctx_storage.get(user_id)
    if not data:
        await message.answer("❌ Ошибка состояния. Начните заново.")
        await labeler.state_dispenser.delete(user_id)
        return

    try:
        parsed_data = parse_student_data(text)
        is_valid, error = validate_student_data(parsed_data)
        if not is_valid:
            await message.answer(error)
            return
            
        student_data = prepare_student_data(parsed_data, data["selected_city"])
        
        # Add to Notion
        city_en = CITY_MAPPING.get(data["selected_city"], data["selected_city"])
        crud = NotionStudentCRUD(city_en)
        result = await crud.add_student(data["selected_group_id"], student_data)
        
        if result.get("duplicate"):
            await message.answer(f"⚠️ Дубликат! ID: {result.get('existing_student_id')}")
        else:
            await message.answer("✅ Ученик добавлен!")
            
            # Log action
            user_info = storage.get_user(user_id)
            action_logger.log_action(
                user_id=user_id,
                user_fio=user_info.get("fio", "Unknown"),
                username=user_info.get("username", ""),
                action_type="add_student",
                action_details={"student": student_data},
                city=data["selected_city"],
                role=user_info.get("role")
            )

        await labeler.state_dispenser.delete(user_id)
        ctx_storage.delete(user_id)
        
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

