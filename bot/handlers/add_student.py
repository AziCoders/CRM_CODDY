"""Обработчик добавления ученика"""
import re
import json
import uuid
from datetime import date
from typing import Dict, Any, Tuple
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from bot.states.add_student_state import AddStudentState
from bot.keyboards.add_student_keyboards import (
    CitySelectCallback,
    GroupSelectCallback,
    CancelCallback,
    get_cities_keyboard,
    get_groups_keyboard,
    get_cancel_keyboard
)
from bot.keyboards.reply_keyboards import (
    get_owner_menu,
    get_manager_menu,
    get_teacher_menu,
    get_smm_menu
)
from bot.keyboards.student_notification_keyboards import get_student_processed_keyboard
from bot.services.group_service import GroupService
from bot.services.role_storage import RoleStorage
from bot.services.action_logger import ActionLogger
from bot.config import CITY_MAPPING, BOT_TOKEN, OWNER_ID
from src.CRUD.crud_student import NotionStudentCRUD

router = Router()
group_service = GroupService()
role_storage = RoleStorage()
action_logger = ActionLogger()

# Хранилище для уведомлений (notification_id -> информация об уведомлении)
notification_storage = {}

# Доступные тарифы и статусы
AVAILABLE_TARIFFS = [
    "Группа 2 раза",
    "Группа 3 раза",
    "Группа 1 раз",
    "Индивидуальные 1 раз",
    "Индивидуальные 2 раза",
    "Индивидуальные 3 раза",
    "Индивидуальные 4 раза",
    "Индивидуальные 5 раз",
]

AVAILABLE_STATUSES = [
    "Обучается",
    "Не начал",
    "Закончил",
    "Не обучается",
]


def get_template_message() -> str:
    """Возвращает шаблон для ввода данных"""
    return ("📝 Введите данные ученика в следующем формате:\n\n"
            "<pre>"
            "\"ФИО\": Сусуркиев Абдул-Азиз Назирович,\n"
            "\"Возраст\": 21,\n"
            "\"Дата поступления\": \"2025-11-22\",\n"
            "\"Номер родителя\": +79623331909,\n"
            "\"Имя родителя\": Назир,\n"
            "\"Тариф\": \"Группа 2 раза\",\n"
            "\"Статус\": \"Обучается\",\n"
            "\"Ссылка на WA, TG\": \"\",\n"
            "\"Комментарий\": \"Доп информация\""
            "</pre>\n\n"
            "⚠️ <b>Обязательные поля:</b> ФИО, Возраст, Номер родителя\n"
            "📅 Дата поступления (если не указана, будет установлена сегодняшняя дата)"
            )


def parse_student_data(text: str) -> Dict[str, Any]:
    """
    Парсит данные ученика из текста
    Формат: "Ключ": значение, или "Ключ": "значение",
    """
    data = {}
    text = text.strip()

    # Улучшенный паттерн для поиска пар ключ-значение
    # Ищем: "Ключ": значение или "Ключ": "значение" (может быть многострочным)
    # Учитываем, что значение может содержать запятые внутри кавычек
    pattern = r'"([^"]+)":\s*"([^"]*)"|"([^"]+)":\s*([^,\n]+)'
    matches = re.findall(pattern, text, re.MULTILINE)

    for match in matches:
        if match[0]:  # Случай с кавычками: "Ключ": "значение"
            key = match[0].strip()
            value = match[1].strip()
        else:  # Случай без кавычек: "Ключ": значение
            key = match[2].strip()
            value = match[3].strip()

        # Обработка разных типов данных
        if key == "Возраст":
            try:
                data[key] = int(value)
            except ValueError:
                data[key] = value
        elif key == "Дата поступления":
            data[key] = value
        elif key in ["ФИО", "Номер родителя", "Имя родителя", "Тариф", "Статус",
                     "Ссылка на WA, TG", "Комментарий"]:
            data[key] = value
        else:
            data[key] = value

    return data


def validate_student_data(data: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Валидирует данные ученика
    Возвращает (is_valid, error_message)
    """
    # Проверка обязательных полей
    if not data.get("ФИО"):
        return False, "❌ Поле 'ФИО' обязательно для заполнения"

    if not data.get("Возраст"):
        return False, "❌ Поле 'Возраст' обязательно для заполнения"

    try:
        age = int(data.get("Возраст"))
        if age < 0 or age > 150:
            return False, "❌ Возраст должен быть от 0 до 150"
    except (ValueError, TypeError):
        return False, "❌ Возраст должен быть числом"

    if not data.get("Номер родителя"):
        return False, "❌ Поле 'Номер родителя' обязательно для заполнения"

    # Валидация номера телефона
    phone = data.get("Номер родителя", "")
    phone_digits = re.sub(r"\D", "", phone)
    if len(phone_digits) != 11 or (not phone_digits.startswith("7") and not phone_digits.startswith("8")):
        return False, "❌ Номер телефона должен быть в формате +7XXXXXXXXXX (11 цифр)"

    # Нормализация номера
    if phone_digits.startswith("8"):
        phone_digits = "7" + phone_digits[1:]
    if not phone.startswith("+"):
        data["Номер родителя"] = f"+{phone_digits}"
    else:
        data["Номер родителя"] = f"+{phone_digits}"

    # Валидация тарифа
    if data.get("Тариф") and data.get("Тариф") not in AVAILABLE_TARIFFS:
        return False, f"❌ Неверный тариф. Доступные: {', '.join(AVAILABLE_TARIFFS)}"

    # Валидация статуса
    if data.get("Статус") and data.get("Статус") not in AVAILABLE_STATUSES:
        return False, f"❌ Неверный статус. Доступные: {', '.join(AVAILABLE_STATUSES)}"

    return True, ""


def prepare_student_data(data: Dict[str, Any], city_name: str) -> Dict[str, Any]:
    """Подготавливает данные ученика для сохранения"""
    # Устанавливаем дату поступления если не указана
    if not data.get("Дата поступления"):
        today = date.today()
        data["Дата поступления"] = today.strftime("%Y-%m-%d")

    # Устанавливаем значения по умолчанию
    result = {
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

    return result


@router.message(F.text == "Добавить ученика")
async def cmd_add_student(message: Message, state: FSMContext, user_role: str = None):
    """Обработчик кнопки 'Добавить ученика'"""
    # Проверяем права доступа
    if user_role is None or user_role == "pending":
        await message.answer("❌ У вас нет доступа к этой функции")
        return

    # Проверяем права для преподавателя
    if user_role == "teacher":
        user_data = role_storage.get_user(message.from_user.id)
        if user_data:
            user_city = user_data.get("city", "")
            # Преподаватель может добавлять только в свой город
            await state.update_data(selected_city=user_city)
            await state.set_state(AddStudentState.waiting_group)
            # Показываем группы сразу
            groups = group_service.get_city_groups(user_city)
            if not groups:
                await message.answer(f"❌ Группы не найдены для города '{user_city}'")
                await state.clear()
                return
            # Получаем количество мест в городе
            city_seats = group_service.get_city_seats(user_city)
            seats_text = f"\n📊 Мест в классе: {city_seats}" if city_seats > 0 else ""
            
            await message.answer(
                f"🏙️ Город: {user_city}{seats_text}\n\n"
                f"Выберите группу:",
                reply_markup=get_groups_keyboard(groups)
            )
            return

    # Для остальных ролей показываем выбор города
    await message.answer(
        "🏙️ Выберите город:",
        reply_markup=get_cities_keyboard()
    )
    await state.set_state(AddStudentState.waiting_city)


@router.callback_query(CitySelectCallback.filter(), AddStudentState.waiting_city)
async def process_city_selection(
        callback: CallbackQuery,
        callback_data: CitySelectCallback,
        state: FSMContext
):
    """Обработка выбора города"""
    city_name = callback_data.city
    await state.update_data(selected_city=city_name)

    # Загружаем группы для города
    groups = group_service.get_city_groups(city_name)

    if not groups:
        await callback.message.edit_text(f"❌ Группы не найдены для города '{city_name}'")
        await callback.answer("Группы не найдены", show_alert=True)
        await state.clear()
        return

    # Получаем количество мест в городе
    city_seats = group_service.get_city_seats(city_name)
    seats_text = f"\n📊 Мест в классе: {city_seats}" if city_seats > 0 else ""
    
    await callback.message.edit_text(
        f"🏙️ Город: {city_name}{seats_text}\n\n"
        f"Выберите группу:",
        reply_markup=get_groups_keyboard(groups)
    )
    await callback.answer()
    await state.set_state(AddStudentState.waiting_group)


@router.callback_query(GroupSelectCallback.filter(), AddStudentState.waiting_group)
async def process_group_selection(
        callback: CallbackQuery,
        callback_data: GroupSelectCallback,
        state: FSMContext
):
    """Обработка выбора группы"""
    group_id = callback_data.group_id
    state_data = await state.get_data()
    city_name = state_data.get("selected_city")

    # Получаем название группы
    groups = group_service.get_city_groups(city_name)
    group_name = "Неизвестная группа"
    for group in groups:
        if group.get("group_id") == group_id:
            group_name = group.get("group_name")
            break

    await state.update_data(selected_group_id=group_id, selected_group_name=group_name)

    await callback.message.edit_text(
        f"🏙️ Город: {city_name}\n"
        f"🏫 Группа: {group_name}\n\n"
        f"{get_template_message()}\n\n"
        f"💡 <i>Напишите 'Отмена' для отмены добавления</i>",
        parse_mode='HTML',
        reply_markup=get_cancel_keyboard()
    )
    await callback.answer()
    await state.set_state(AddStudentState.waiting_data)


@router.message(AddStudentState.waiting_data)
async def process_student_data(message: Message, state: FSMContext, user_role: str = None):
    """Обработка ввода данных ученика"""
    # Проверяем, не нажата ли кнопка отмены
    if message.text and message.text.strip().lower() in ["отмена", "❌ отмена", "/отмена"]:
        await cancel_add_student(message, state, user_role)
        return

    state_data = await state.get_data()
    city_name = state_data.get("selected_city")
    group_id = state_data.get("selected_group_id")
    group_name = state_data.get("selected_group_name")

    if not city_name or not group_id:
        await message.answer("❌ Ошибка: не выбран город или группа. Начните заново.")
        await state.clear()
        return

    # Парсим данные
    try:
        data = parse_student_data(message.text)
    except Exception as e:
        await message.answer(
            f"❌ Ошибка при разборе данных: {str(e)}\n\n"
            f"Пожалуйста, используйте правильный формат:\n"
            f"{get_template_message()}",
        )
        return

    # Валидируем данные
    is_valid, error_msg = validate_student_data(data)
    if not is_valid:
        await message.answer(error_msg)
        return

    # Подготавливаем данные
    student_data = prepare_student_data(data, city_name)

    # Добавляем ученика через CRUD
    try:
        # Преобразуем русское название города в английское для CRUD
        city_en = CITY_MAPPING.get(city_name, city_name)
        crud = NotionStudentCRUD(city_en)

        result = await crud.add_student(group_id, student_data, force=False)

        if result.get("duplicate"):
            await message.answer(
                f"⚠️ Ученик с таким ФИО уже существует в группе '{group_name}'\n\n"
                f"ID существующего ученика: {result.get('existing_student_id')}"
            )
        else:
            # Логируем действие
            user_data = role_storage.get_user(message.from_user.id)
            action_logger.log_action(
                user_id=message.from_user.id,
                user_fio=user_data.get("fio", message.from_user.full_name) if user_data else message.from_user.full_name,
                username=message.from_user.username or "нет",
                action_type="add_student",
                action_details={
                    "student": {
                        **student_data,
                        "group_name": group_name,
                        "student_id": result.get("student_id", "")
                    }
                },
                city=city_name,
                role=user_data.get("role") if user_data else None
            )
            
            await message.answer(
                f"✅ Ученик успешно добавлен!\n\n"
                f"👤 ФИО: {student_data['ФИО']}\n"
                f"🏫 Группа: {group_name}\n"
                f"🏙️ Город: {city_name}"
            )
            
            # Отправляем уведомления менеджерам и владельцу
            try:
                student_id = result.get("student_id", "")
                print(f"📞 Вызываю функцию отправки уведомлений для ученика ID: {student_id}")
                await send_student_notifications(
                    student_data=student_data,
                    group_name=group_name,
                    city_name=city_name,
                    student_id=student_id,
                    added_by_user=message.from_user
                )
            except Exception as e:
                print(f"❌ Ошибка при вызове send_student_notifications: {e}")
                import traceback
                traceback.print_exc()

        await state.clear()

    except ValueError as e:
        # Обработка ошибки лимита мест или других валидационных ошибок
        error_msg = str(e)
        if "Лимит учеников исчерпан" in error_msg or "лимит" in error_msg.lower():
            await message.answer(
                f"❌ {error_msg}\n\n"
                f"🏫 Группа: {group_name}\n"
                f"🏙️ Город: {city_name}\n\n"
                f"Пожалуйста, выберите другую группу."
            )
        else:
            await message.answer(
                f"❌ Ошибка при добавлении ученика: {error_msg}"
            )
        print(f"Ошибка добавления ученика: {e}")
    except Exception as e:
        await message.answer(
            f"❌ Ошибка при добавлении ученика: {str(e)}"
        )
        print(f"Ошибка добавления ученика: {e}")


async def send_student_notifications(
    student_data: Dict[str, Any],
    group_name: str,
    city_name: str,
    student_id: str,
    added_by_user
):
    """Отправляет уведомления менеджерам и владельцу о новом ученике"""
    print(f"🔔 Начинаю отправку уведомлений о новом ученике: {student_data.get('ФИО', 'N/A')}")
    
    # Получаем всех менеджеров и владельца
    all_users = role_storage.get_all_users()
    print(f"📋 Всего пользователей в системе: {len(all_users)}")
    
    managers_and_owner = [
        user for user in all_users 
        if user.get("role") in ["manager", "owner"]
    ]
    print(f"👥 Найдено менеджеров и владельцев в roles.json: {len(managers_and_owner)}")
    
    # Добавляем владельца, если его нет в списке
    owner_in_list = any(user.get("user_id") == OWNER_ID for user in managers_and_owner)
    if not owner_in_list:
        print(f"👑 Добавляю владельца (ID: {OWNER_ID}) в список получателей")
        managers_and_owner.append({
            "user_id": OWNER_ID,
            "fio": "Владелец",
            "username": "owner",
            "role": "owner"
        })
    
    print(f"📤 Всего получателей уведомлений: {len(managers_and_owner)}")
    for user in managers_and_owner:
        print(f"   - {user.get('fio', 'N/A')} (ID: {user.get('user_id')}, роль: {user.get('role')})")
    
    if not managers_and_owner:
        print("⚠️ Нет получателей для уведомлений")
        return
    
    # Создаем уникальный ID для этого уведомления
    notification_id = str(uuid.uuid4())
    
    # Формируем текст уведомления
    added_by_name = added_by_user.full_name or "Неизвестно"
    added_by_username = added_by_user.username or "нет"
    
    notification_text = (
        f"🔔 <b>Добавлен новый ученик</b>\n\n"
        f"👤 <b>ФИО:</b> {student_data.get('ФИО', 'Не указано')}\n"
        f"📞 <b>Номер родителя:</b> {student_data.get('Номер родителя', 'Не указано')}\n"
        f"👨‍👩‍👧 <b>Имя родителя:</b> {student_data.get('Имя родителя', 'Не указано')}\n"
        f"🎂 <b>Возраст:</b> {student_data.get('Возраст', 'Не указано')}\n"
        f"📅 <b>Дата поступления:</b> {student_data.get('Дата поступления', 'Не указано')}\n"
        f"💰 <b>Тариф:</b> {student_data.get('Тариф', 'Не указано')}\n"
        f"📊 <b>Статус:</b> {student_data.get('Статус', 'Не указано')}\n"
        f"🏫 <b>Группа:</b> {group_name}\n"
        f"🏙️ <b>Город:</b> {city_name}\n\n"
        f"➕ <b>Добавил:</b> {added_by_name} (@{added_by_username})"
    )
    
    # Отправляем уведомления
    bot = Bot(token=BOT_TOKEN)
    notification_messages = []  # Список {user_id, message_id}
    
    try:
        for user in managers_and_owner:
            user_id = user.get("user_id")
            if not user_id:
                print(f"⚠️ Пропуск пользователя без ID: {user}")
                continue
            
            try:
                print(f"📨 Отправляю уведомление пользователю {user.get('fio', 'N/A')} (ID: {user_id})")
                sent_message = await bot.send_message(
                    chat_id=user_id,
                    text=notification_text,
                    reply_markup=get_student_processed_keyboard(student_id, notification_id),
                    parse_mode="HTML"
                )
                print(f"✅ Уведомление успешно отправлено пользователю {user_id} (message_id: {sent_message.message_id})")
                notification_messages.append({
                    "user_id": user_id,
                    "message_id": sent_message.message_id
                })
            except Exception as e:
                print(f"❌ Ошибка отправки уведомления пользователю {user_id} ({user.get('fio', 'N/A')}): {e}")
                import traceback
                traceback.print_exc()
                continue
        
        print(f"📊 Успешно отправлено уведомлений: {len(notification_messages)} из {len(managers_and_owner)}")
        
        # Сохраняем информацию о сообщениях
        if notification_messages:
            notification_storage[notification_id] = {
                "student_id": student_id,
                "messages": notification_messages,
                "student_data": student_data,
                "group_name": group_name,
                "city_name": city_name
            }
            print(f"💾 Информация об уведомлении сохранена (notification_id: {notification_id})")
        else:
            print("⚠️ Не удалось отправить ни одного уведомления")
    except Exception as e:
        print(f"❌ Критическая ошибка при отправке уведомлений: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await bot.session.close()
        print("🔚 Сессия бота закрыта")


async def cancel_add_student(message: Message, state: FSMContext, user_role: str = None):
    """Отмена добавления ученика и возврат в главное меню"""
    await state.clear()

    # Возвращаем пользователя в главное меню в зависимости от роли
    if user_role == "owner":
        await message.answer(
            "❌ Добавление ученика отменено.",
            reply_markup=get_owner_menu()
        )
    elif user_role == "manager":
        await message.answer(
            "❌ Добавление ученика отменено.",
            reply_markup=get_manager_menu()
        )
    elif user_role == "teacher":
        await message.answer(
            "❌ Добавление ученика отменено.",
            reply_markup=get_teacher_menu()
        )
    elif user_role == "smm":
        await message.answer(
            "❌ Добавление ученика отменено.",
            reply_markup=get_smm_menu()
        )
    else:
        await message.answer("❌ Добавление ученика отменено.")


@router.callback_query(CancelCallback.filter())
async def handle_cancel_callback(
        callback: CallbackQuery,
        state: FSMContext,
        user_role: str = None
):
    """Обработчик кнопки отмены через callback"""
    await state.clear()

    # Удаляем сообщение о добавлении
    try:
        await callback.message.delete()
    except Exception:
        # Если не удалось удалить, редактируем
        await callback.message.edit_text("❌ Добавление ученика отменено.")

    # Возвращаем пользователя в главное меню в зависимости от роли
    if user_role == "owner":
        await callback.message.answer(
            "👑 Главное меню:",
            reply_markup=get_owner_menu()
        )
    elif user_role == "manager":
        await callback.message.answer(
            "👨‍💼 Главное меню:",
            reply_markup=get_manager_menu()
        )
    elif user_role == "teacher":
        await callback.message.answer(
            "👨‍🏫 Главное меню:",
            reply_markup=get_teacher_menu()
        )
    elif user_role == "smm":
        await callback.message.answer(
            "📱 Главное меню:",
            reply_markup=get_smm_menu()
        )

    await callback.answer("Добавление отменено")
