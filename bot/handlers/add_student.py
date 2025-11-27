"""Обработчик добавления ученика"""
import re
import json
from datetime import date
from typing import Dict, Any, Tuple
from aiogram import Router, F
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
from bot.services.group_service import GroupService
from bot.services.role_storage import RoleStorage
from bot.config import CITY_MAPPING
from src.CRUD.crud_student import NotionStudentCRUD

router = Router()
group_service = GroupService()
role_storage = RoleStorage()

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
            await message.answer(
                f"✅ Ученик успешно добавлен!\n\n"
                f"👤 ФИО: {student_data['ФИО']}\n"
                f"🏫 Группа: {group_name}\n"
                f"🏙️ Город: {city_name}"
            )

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
