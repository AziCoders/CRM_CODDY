"""Обработчик отметки оплаты"""
from typing import Optional, Tuple
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter, BaseFilter
from bot.states.payment_state import PaymentState
from bot.services.payment_service import PaymentService
from bot.services.student_search import StudentSearchService
from bot.services.role_storage import RoleStorage
from bot.services.action_logger import ActionLogger
from bot.keyboards.payment_keyboards import (
    PaymentStatusCallback,
    PaymentBackCallback,
    PaymentCityCallback,
    PaymentStudentCallback,
    PaymentPaginationCallback,
    PaymentAddCommentCallback,
    get_payment_status_keyboard,
    get_payment_cities_keyboard,
    get_payment_students_keyboard,
    get_only_comment_keyboard
)
from bot.config import CITIES
from bot.keyboards.reply_keyboards import (
    get_owner_menu,
    get_manager_menu,
    get_teacher_menu
)

router = Router()
payment_service = PaymentService()
search_service = StudentSearchService()
role_storage = RoleStorage()
action_logger = ActionLogger()


class PaymentQueryFilter(BaseFilter):
    """Фильтр для проверки, является ли сообщение запросом на оплату"""

    async def __call__(self, message: Message, *args, **kwargs) -> bool:
        if not message.text:
            return False
        text_lower = message.text.strip().lower()
        payment_prefixes = ["оплата", "олпата"]
        return any(text_lower.startswith(prefix) for prefix in payment_prefixes)


def parse_payment_query(text: str) -> Optional[Tuple[str, str]]:
    """
    Парсит запрос в формате "Оплата <город> <запрос>" или "Олпата <город> <запрос>"
    Возвращает (город, запрос) или None
    """
    text = text.strip()

    # Проверяем, начинается ли с "Оплата" или "Олпата"
    payment_prefixes = ["оплата", "олпата"]
    query_start = None

    for prefix in payment_prefixes:
        if text.lower().startswith(prefix):
            query_start = len(prefix)
            break

    if query_start is None:
        return None

    # Убираем префикс и лишние пробелы
    rest = text[query_start:].strip()

    # Ищем город в оставшейся части
    for city in CITIES:
        if rest.lower().startswith(city.lower()):
            query = rest[len(city):].strip()
            if query:
                return (city, query)

    return None


def format_payment_info(student_data: dict, payment_data: Optional[dict], city_name: str) -> str:
    """Форматирует информацию об ученике с данными об оплате и посещаемости"""
    return payment_service.format_student_info_with_payment_and_attendance(student_data, payment_data, city_name)


@router.message(F.text, ~F.text.startswith("/"), PaymentQueryFilter())
async def handle_payment_search(message: Message, state: FSMContext, user_role: str = None):
    """Обработчик поиска для оплаты"""
    # Проверяем права доступа
    if user_role is None or user_role == "pending":
        return  # Не обрабатываем для незарегистрированных

    # Пропускаем, если пользователь в FSM состоянии добавления ученика или посещаемости
    current_state = await state.get_state()
    if current_state:
        state_str = str(current_state)
        # Пропускаем если в других состояниях (кроме оплаты)
        if "AddStudentState" in state_str or "AttendanceState" in state_str:
            return

    # Пропускаем кнопки меню
    menu_buttons = ["Добавить ученика", "Посещаемость", "Города", "Оплаты",
                    "Синхронизация", "Отчёты", "ИИ-отчёт", "Свободные места",
                    "Управление ролями", "Отмена"]
    if message.text in menu_buttons:
        return

    text = message.text.strip() if message.text else ""

    # Парсим запрос на оплату
    parsed = parse_payment_query(text)
    if not parsed:
        return  # Не наш формат, пропускаем

    city_name, query = parsed

    # Проверяем права доступа к городу
    if user_role == "teacher":
        # Преподаватель может работать только в своем городе
        user_data = role_storage.get_user(message.from_user.id)
        if user_data:
            user_city_name = user_data.get("city", "")
            if user_city_name != city_name:
                await message.answer(
                    f"❌ У вас нет доступа к городу '{city_name}'. "
                    f"Вы можете работать только в городе '{user_city_name}'."
                )
                return

    # Выполняем поиск ученика
    try:
        result_type, data = search_service.search(city_name, query)

        if result_type == "not_found":
            await message.answer(
                f"❌ Ученик не найден в городе '{city_name}' по запросу: {query}"
            )
        elif result_type == "full_info":
            # Нашли одного ученика - показываем информацию об оплате
            student_data = data

            # Получаем информацию об оплате
            payment_data = payment_service.get_student_payment_info(city_name, student_data)

            # Форматируем и показываем информацию
            formatted = format_payment_info(student_data, payment_data, city_name)

            # Сохраняем данные в состояние
            await state.update_data(
                student_data=student_data,
                payment_data=payment_data,
                city_name=city_name
            )
            await state.set_state(PaymentState.waiting_status)

            await message.answer(
                formatted,
                parse_mode="HTML",
                reply_markup=get_payment_status_keyboard()
            )
        elif result_type == "list":
            # Нашли несколько учеников - показываем список
            await message.answer(
                "⚠️ Найдено несколько учеников. Пожалуйста, уточните запрос (ФИО или телефон)."
            )

    except Exception as e:
        await message.answer(
            f"❌ Произошла ошибка при поиске: {str(e)}"
        )
        print(f"Ошибка поиска для оплаты: {e}")


@router.callback_query(PaymentStatusCallback.filter(), PaymentState.waiting_status)
async def process_payment_status(
        callback: CallbackQuery,
        callback_data: PaymentStatusCallback,
        state: FSMContext,
        user_role: str = None
):
    """Обработка выбора статуса оплаты"""
    new_status = callback_data.status
    data = await state.get_data()

    student_data = data.get("student_data")
    city_name = data.get("city_name")

    if not student_data or not city_name:
        await callback.answer("❌ Ошибка: данные ученика не найдены", show_alert=True)
        await state.clear()
        return

    # Определяем идентификатор для поиска (используем ФИО)
    student_identifier = student_data.get("ФИО", "").strip()

    if not student_identifier:
        await callback.answer("❌ Ошибка: не найдено ФИО ученика", show_alert=True)
        await state.clear()
        return

    # Получаем старый статус перед обновлением
    payment_data = payment_service.get_student_payment_info(city_name, student_data)
    current_month = payment_service.get_current_month(city_name)
    old_status = payment_service.get_payment_status_for_month(payment_data, current_month) if payment_data else ""
    old_status = old_status if old_status else "Не указан"

    # Показываем процесс сохранения
    await callback.message.edit_text("⏳ Сохранение статуса оплаты...")
    await callback.answer()

    # Обновляем статус в Notion
    success = await payment_service.update_payment_status(
        city_name=city_name,
        student_identifier=student_identifier,
        status=new_status
    )

    if success:
        # Получаем данные ученика для форматирования
        fio = student_data.get("ФИО", "Не указано").strip()
        student_url = student_data.get("student_url", "")

        # Логируем действие
        user_data = role_storage.get_user(callback.from_user.id)
        action_logger.log_action(
            user_id=callback.from_user.id,
            user_fio=user_data.get("fio", callback.from_user.full_name) if user_data else callback.from_user.full_name,
            username=callback.from_user.username or "нет",
            action_type="update_payment",
            action_details={
                "student_fio": fio,
                "status": new_status,
                "old_status": old_status,
                "month": current_month
            },
            city=city_name,
            role=user_data.get("role") if user_data else None
        )

        # Формируем короткое сообщение
        fio_line = f"👤 <a href='{student_url}'>{fio}</a>" if student_url else f"👤 {fio}"
        status_message = (
            f"Статус оплаты {fio_line} за {current_month} обновлен\n"
            f"с <b>{old_status}</b> на <b>{new_status}</b>"
        )

        # Сохраняем данные для возможного добавления комментария
        await state.update_data(
            student_data=student_data,
            city_name=city_name,
            student_identifier=student_identifier
        )

        await callback.message.edit_text(
            status_message,
            parse_mode="HTML",
            reply_markup=get_only_comment_keyboard()
        )
        # Устанавливаем состояние для возможности добавления комментария
        await state.set_state(PaymentState.waiting_status)
    else:
        await callback.message.edit_text(
            "❌ Ошибка при сохранении статуса оплаты.\n"
            "Пожалуйста, попробуйте снова."
        )
        await state.clear()


@router.message(F.text == "Оплаты")
async def cmd_payments(message: Message, state: FSMContext, user_role: str = None):
    """Обработчик кнопки 'Оплаты'"""
    # Проверяем права доступа
    if user_role is None or user_role == "pending":
        await message.answer("❌ У вас нет доступа к этой функции")
        return

    # Проверяем доступность функции для роли
    if user_role not in ["owner", "manager", "teacher"]:
        await message.answer("❌ Оплаты доступны только для владельца, менеджера и преподавателя")
        return

    # Для преподавателя - сразу показываем учеников его города
    if user_role == "teacher":
        user_data = role_storage.get_user(message.from_user.id)
        if not user_data:
            await message.answer("❌ Не удалось определить ваш город")
            return

        user_city = user_data.get("city", "")
        if not user_city:
            await message.answer("❌ У вас не назначен город")
            return

        # Сохраняем город в состояние
        await state.update_data(selected_city=user_city)
        await state.set_state(PaymentState.waiting_student)

        # Получаем учеников города
        students = payment_service.get_city_students(user_city)
        if not students:
            await message.answer(f"❌ Ученики не найдены для города '{user_city}'")
            await state.clear()
            return

        # Показываем первую страницу (по 10 учеников)
        page = 0
        page_size = 10
        total_pages = (len(students) + page_size - 1) // page_size
        page_students = students[page * page_size:(page + 1) * page_size]

        # Получаем статусы оплаты для учеников на странице
        student_ids = [s.get("ID", "") for s in page_students]
        payment_statuses = payment_service.get_payment_statuses_for_students(user_city, student_ids)

        await state.update_data(students=students, current_page=page)

        await message.answer(
            f"💰 Оплаты\n"
            f"🏙️ Город: {user_city}\n\n"
            f"Выберите ученика (страница {page + 1} из {total_pages}):",
            reply_markup=get_payment_students_keyboard(page_students, user_city, page, total_pages, payment_statuses)
        )
        return

    # Для владельца и менеджера - сначала выбор города
    await message.answer(
        "💰 Оплаты\n\n"
        "🏙️ Выберите город:",
        reply_markup=get_payment_cities_keyboard()
    )
    await state.set_state(PaymentState.waiting_city)


@router.callback_query(PaymentCityCallback.filter(), PaymentState.waiting_city)
async def process_payment_city(
        callback: CallbackQuery,
        callback_data: PaymentCityCallback,
        state: FSMContext
):
    """Обработка выбора города при оплате"""
    city_name = callback_data.city
    await state.update_data(selected_city=city_name)

    # Получаем учеников города
    students = payment_service.get_city_students(city_name)

    if not students:
        await callback.message.edit_text(f"❌ Ученики не найдены для города '{city_name}'")
        await callback.answer("Ученики не найдены", show_alert=True)
        await state.clear()
        return

    # Показываем первую страницу (по 10 учеников)
    page = 0
    page_size = 10
    total_pages = (len(students) + page_size - 1) // page_size
    page_students = students[page * page_size:(page + 1) * page_size]

    # Получаем статусы оплаты для учеников на странице
    student_ids = [s.get("ID", "") for s in page_students]
    payment_statuses = payment_service.get_payment_statuses_for_students(city_name, student_ids)

    await state.update_data(students=students, current_page=page)
    await state.set_state(PaymentState.waiting_student)

    await callback.message.edit_text(
        f"💰 Оплаты\n"
        f"🏙️ Город: {city_name}\n\n"
        f"Выберите ученика (страница {page + 1} из {total_pages}):",
        reply_markup=get_payment_students_keyboard(page_students, city_name, page, total_pages, payment_statuses)
    )
    await callback.answer()


@router.callback_query(PaymentPaginationCallback.filter(), PaymentState.waiting_student)
async def process_payment_pagination(
        callback: CallbackQuery,
        callback_data: PaymentPaginationCallback,
        state: FSMContext
):
    """Обработка пагинации списка учеников"""
    city_name = callback_data.city
    page = callback_data.page

    data = await state.get_data()
    students = data.get("students", [])

    if not students:
        await callback.answer("❌ Список учеников не найден", show_alert=True)
        return

    # Показываем страницу
    page_size = 10
    total_pages = (len(students) + page_size - 1) // page_size

    if page < 0 or page >= total_pages:
        await callback.answer("❌ Неверная страница", show_alert=True)
        return

    page_students = students[page * page_size:(page + 1) * page_size]

    # Получаем статусы оплаты для учеников на странице
    student_ids = [s.get("ID", "") for s in page_students]
    data = await state.get_data()
    selected_city = data.get("selected_city", city_name)
    payment_statuses = payment_service.get_payment_statuses_for_students(selected_city, student_ids)

    await state.update_data(current_page=page)

    await callback.message.edit_text(
        f"💰 Оплаты\n"
        f"🏙️ Город: {city_name}\n\n"
        f"Выберите ученика (страница {page + 1} из {total_pages}):",
        reply_markup=get_payment_students_keyboard(page_students, city_name, page, total_pages, payment_statuses)
    )
    await callback.answer()


@router.callback_query(PaymentStudentCallback.filter(), PaymentState.waiting_student)
async def process_payment_student(
        callback: CallbackQuery,
        callback_data: PaymentStudentCallback,
        state: FSMContext
):
    """Обработка выбора ученика"""
    student_id = callback_data.student_id
    data = await state.get_data()
    city_name = data.get("selected_city")

    if not city_name:
        await callback.answer("❌ Ошибка: город не выбран", show_alert=True)
        await state.clear()
        return

    # Получаем данные ученика
    student_data = payment_service.get_student_by_id(city_name, student_id)

    if not student_data:
        await callback.answer("❌ Ученик не найден", show_alert=True)
        return

    # Получаем информацию об оплате
    payment_data = payment_service.get_student_payment_info(city_name, student_data)

    # Форматируем и показываем информацию
    formatted = format_payment_info(student_data, payment_data, city_name)

    # Сохраняем данные в состояние
    await state.update_data(
        student_data=student_data,
        payment_data=payment_data,
        city_name=city_name
    )
    await state.set_state(PaymentState.waiting_status)

    await callback.message.edit_text(
        formatted,
        parse_mode="HTML",
        reply_markup=get_payment_status_keyboard()
    )
    await callback.answer()


@router.callback_query(PaymentBackCallback.filter())
async def process_payment_back(
        callback: CallbackQuery,
        state: FSMContext,
        user_role: str = None
):
    """Обработка кнопки 'Назад' или 'Отмена'"""
    current_state = await state.get_state()
    state_str = str(current_state) if current_state else ""

    # Если в состоянии ввода комментария - возвращаемся к статусу (но это не callback, это message)
    # Этот обработчик только для callback, поэтому состояние waiting_comment обрабатывается через message

    # Если в состоянии выбора статуса - отменяем
    if "waiting_status" in state_str:
        await callback.message.edit_text("❌ Отметка оплаты отменена")
        await callback.answer("Отменено")
        await state.clear()
        return

    # Если в состоянии выбора ученика - возвращаемся к выбору города
    if "waiting_student" in state_str:
        data = await state.get_data()
        city_name = data.get("selected_city")

        # Для преподавателя просто очищаем состояние
        if user_role == "teacher":
            await callback.message.edit_text("❌ Операция отменена")
            await callback.answer("Отменено")
            await state.clear()
            return

        # Для владельца/менеджера - возвращаемся к выбору города
        await callback.message.edit_text(
            "💰 Оплаты\n\n"
            "🏙️ Выберите город:",
            reply_markup=get_payment_cities_keyboard()
        )
        await callback.answer()
        await state.set_state(PaymentState.waiting_city)
        return


@router.callback_query(PaymentAddCommentCallback.filter(), PaymentState.waiting_status)
async def process_add_comment(
        callback: CallbackQuery,
        state: FSMContext
):
    """Обработка кнопки 'Добавить комментарий'"""
    await callback.message.answer(
        "💬 Введите комментарий к оплате:\n\n"
        "Для отмены отправьте /stop"
    )
    await callback.answer()
    await state.set_state(PaymentState.waiting_comment)


@router.message(PaymentState.waiting_comment, F.text == "/stop")
async def cancel_comment(message: Message, state: FSMContext):
    """Отмена ввода комментария"""
    await message.answer("❌ Ввод комментария отменен")
    await state.clear()


@router.message(PaymentState.waiting_comment, F.text)
async def process_comment_input(message: Message, state: FSMContext):
    """Обработка ввода комментария"""
    comment = message.text.strip()

    if not comment:
        await message.answer("❌ Комментарий не может быть пустым. Попробуйте снова или отправьте /stop для отмены.")
        return

    data = await state.get_data()
    student_identifier = data.get("student_identifier")
    city_name = data.get("city_name")
    student_data = data.get("student_data")

    if not student_identifier or not city_name:
        await message.answer("❌ Ошибка: данные ученика не найдены")
        await state.clear()
        return

    # Показываем процесс сохранения
    await message.answer("⏳ Сохранение комментария...")

    # Обновляем комментарий в Notion
    success = await payment_service.update_payment_comment(
        city_name=city_name,
        student_identifier=student_identifier,
        comment=comment
    )

    if success:
        # Логируем действие
        user_data = role_storage.get_user(message.from_user.id)
        action_logger.log_action(
            user_id=message.from_user.id,
            user_fio=user_data.get("fio", message.from_user.full_name) if user_data else message.from_user.full_name,
            username=message.from_user.username or "нет",
            action_type="update_payment",
            action_details={
                "student_fio": student_data.get("ФИО", ""),
                "comment": comment,
                "action": "add_comment"
            },
            city=city_name,
            role=user_data.get("role") if user_data else None
        )
        
        await message.answer(
            f"✅ Комментарий добавлен:\n{comment}"
        )
        await state.clear()
    else:
        await message.answer(
            "❌ Ошибка при сохранении комментария.\n"
            "Пожалуйста, попробуйте снова."
        )
        await state.clear()
