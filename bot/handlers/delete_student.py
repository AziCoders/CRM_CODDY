"""Обработчик удаления ученика"""
from aiogram import Router, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from bot.keyboards.student_profile_keyboards import StudentDeleteCallback, StudentPaymentCallback
from bot.states.delete_student_state import DeleteStudentState
from bot.states.payment_state import PaymentState
from bot.services.student_search import StudentSearchService
from bot.services.payment_service import PaymentService
from bot.services.role_storage import RoleStorage
from bot.services.action_logger import ActionLogger
from bot.config import CITY_MAPPING
from src.CRUD.crud_student import NotionStudentCRUD
from bot.keyboards.reply_keyboards import (
    get_owner_menu,
    get_manager_menu,
    get_teacher_menu,
    get_smm_menu
)

router = Router()
search_service = StudentSearchService()
payment_service = PaymentService()
role_storage = RoleStorage()
action_logger = ActionLogger()


@router.callback_query(StudentPaymentCallback.filter())
async def handle_student_payment(
    callback: CallbackQuery,
    callback_data: StudentPaymentCallback,
    state: FSMContext,
    user_role: str = None
):
    """Обработка кнопки Оплата из профиля ученика"""
    if user_role is None or user_role == "pending":
        await callback.answer("❌ У вас нет доступа", show_alert=True)
        return
    
    student_id_short = callback_data.student_id
    city_en = callback_data.city_en
    
    # Преобразуем английское название обратно в русское
    from bot.config import CITY_MAPPING
    city_name = None
    for ru_name, en_name in CITY_MAPPING.items():
        if en_name == city_en or en_name.startswith(city_en):
            city_name = ru_name
            break
    
    if not city_name:
        city_name = city_en  # Fallback
    
    # Получаем данные ученика
    try:
        # Ищем ученика по ID в файле students.json
        students_data = search_service._load_city_students(city_name)
        
        student_data = None
        student_id = None
        for group_id, group_data in students_data.items():
            for student in group_data.get("students", []):
                # Ищем по частичному совпадению (первые символы UUID)
                student_id_from_data = student.get("ID", "")
                student_id_no_dashes = student_id_from_data.replace("-", "")
                # Проверяем, начинается ли ID с сокращенного значения
                if student_id_no_dashes.startswith(student_id_short):
                    student_data = student.copy()
                    student_data["group_name"] = group_data.get("group_name", "")
                    student_data["group_id"] = group_id
                    student_id = student_id_from_data  # Используем полный ID
                    break
            if student_data:
                break
        
        if not student_data:
            await callback.answer("❌ Ученик не найден", show_alert=True)
            return
        
        # Получаем информацию об оплате
        payment_data = payment_service.get_student_payment_info(city_name, student_data)
        
        # Форматируем информацию
        formatted = payment_service.format_student_info_with_payment_and_attendance(student_data, payment_data, city_name)
        
        # Сохраняем данные в состояние
        await state.update_data(
            student_data=student_data,
            payment_data=payment_data,
            city_name=city_name
        )
        await state.set_state(PaymentState.waiting_status)
        
        # Показываем клавиатуру оплаты
        from bot.keyboards.payment_keyboards import get_payment_status_keyboard
        await callback.message.edit_text(
            formatted,
            parse_mode="HTML",
            reply_markup=get_payment_status_keyboard()
        )
        await callback.answer()
        
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
        print(f"Ошибка при обработке оплаты: {e}")


@router.callback_query(StudentDeleteCallback.filter())
async def handle_student_delete(
    callback: CallbackQuery,
    callback_data: StudentDeleteCallback,
    state: FSMContext,
    user_role: str = None
):
    """Обработка кнопки Удалить из профиля ученика"""
    if user_role is None or user_role == "pending":
        await callback.answer("❌ У вас нет доступа", show_alert=True)
        return
    
    # Проверяем права (только owner, manager могут удалять)
    if user_role not in ["owner", "manager"]:
        await callback.answer("❌ Только владелец и менеджер могут удалять учеников", show_alert=True)
        return
    
    student_id_short = callback_data.student_id
    city_en = callback_data.city_en
    group_id_short = callback_data.group_id
    
    # Преобразуем английское название обратно в русское
    from bot.config import CITY_MAPPING
    city_name = None
    for ru_name, en_name in CITY_MAPPING.items():
        if en_name == city_en or en_name.startswith(city_en):
            city_name = ru_name
            break
    
    if not city_name:
        city_name = city_en  # Fallback
    
    # Ищем ученика по сокращенному ID для получения полных данных
    try:
        students_data = search_service._load_city_students(city_name)
        student_id = None
        group_id = None
        
        for group_id_key, group_data in students_data.items():
            for student in group_data.get("students", []):
                student_id_from_data = student.get("ID", "")
                student_id_no_dashes = student_id_from_data.replace("-", "")
                # Проверяем, начинается ли ID с сокращенного значения
                if student_id_no_dashes.startswith(student_id_short):
                    student_id = student_id_from_data
                    # Если group_id_short указан, проверяем совпадение
                    if group_id_short:
                        group_id_no_dashes = group_id_key.replace("-", "")
                        if group_id_no_dashes.startswith(group_id_short):
                            group_id = group_id_key
                        else:
                            group_id = group_id_key  # Используем найденную группу
                    else:
                        group_id = group_id_key
                    break
            if student_id:
                break
        
        if not student_id:
            await callback.answer("❌ Ученик не найден", show_alert=True)
            return
        
        # Сохраняем данные в состояние
        await state.update_data(
            student_id=student_id,
            city_name=city_name,
            group_id=group_id or ""
        )
    except Exception as e:
        await callback.answer(f"❌ Ошибка при поиске ученика: {str(e)}", show_alert=True)
        print(f"Ошибка при обработке удаления: {e}")
        return
    await state.set_state(DeleteStudentState.waiting_reason)
    
    await callback.message.edit_text(
        "🗑️ <b>Удаление ученика</b>\n\n"
        "📝 Пожалуйста, укажите причину ухода ученика:",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(DeleteStudentState.waiting_reason)
async def process_delete_reason(
    message: Message,
    state: FSMContext,
    user_role: str = None
):
    """Обработка ввода причины удаления"""
    if message.text and message.text.strip().lower() in ["отмена", "❌ отмена", "/отмена"]:
        await state.clear()
        await message.answer("❌ Удаление отменено")
        return
    
    reason = message.text.strip() if message.text else ""
    
    if not reason:
        await message.answer("❌ Пожалуйста, укажите причину ухода ученика")
        return
    
    data = await state.get_data()
    student_id = data.get("student_id")
    city_name = data.get("city_name")
    group_id = data.get("group_id", "")
    
    if not student_id or not city_name:
        await message.answer("❌ Ошибка: данные не найдены. Начните заново.")
        await state.clear()
        return
    
    # Показываем процесс удаления
    await message.answer("⏳ Обрабатываю удаление ученика...")
    
    try:
        # Получаем данные ученика для логирования
        city_en = CITY_MAPPING.get(city_name, city_name)
        students_data = search_service._load_city_students(city_name)
        
        student_fio = "Неизвестно"
        for group_data in students_data.values():
            for student in group_data.get("students", []):
                if student.get("ID") == student_id:
                    student_fio = student.get("ФИО", "Неизвестно")
                    break
            if student_fio != "Неизвестно":
                break
        
        # Выполняем удаление
        crud = NotionStudentCRUD(city_en)
        result = await crud.delete_student(student_id, reason, group_id)
        
        # Формируем сообщение о результате
        success_parts = []
        if result["added_to_left"]:
            success_parts.append("✅ Добавлен в 'Ушедшие ученики'")
        if result["archived_from_students"]:
            success_parts.append("✅ Удален из основной таблицы")
        if result["deleted_from_attendance"]:
            success_parts.append("✅ Удален из посещаемости")
        if result["deleted_from_payments"]:
            success_parts.append("✅ Удален из оплат")
        
        error_parts = result.get("errors", [])
        
        # Формируем итоговое сообщение
        message_text = f"🗑️ <b>Ученик удален</b>\n\n"
        message_text += f"👤 <b>ФИО:</b> {student_fio}\n"
        message_text += f"📝 <b>Причина:</b> {reason}\n\n"
        
        if success_parts:
            message_text += "<b>Выполнено:</b>\n" + "\n".join(success_parts) + "\n\n"
        
        if error_parts:
            message_text += "<b>⚠️ Ошибки (частично выполнено):</b>\n" + "\n".join(error_parts[:5])  # Показываем первые 5 ошибок
        
        # Логируем действие
        user_data = role_storage.get_user(message.from_user.id)
        action_logger.log_action(
            user_id=message.from_user.id,
            user_fio=user_data.get("fio", message.from_user.full_name) if user_data else message.from_user.full_name,
            username=message.from_user.username or "нет",
            action_type="delete_student",
            action_details={
                "student": {
                    "fio": student_fio,
                    "student_id": student_id,
                    "reason": reason,
                    "result": result
                }
            },
            city=city_name,
            role=user_data.get("role") if user_data else None
        )
        
        await message.answer(message_text, parse_mode="HTML")
        await state.clear()
        
    except Exception as e:
        error_msg = f"❌ Критическая ошибка при удалении ученика: {str(e)}"
        await message.answer(error_msg)
        print(f"Ошибка удаления ученика: {e}")
        await state.clear()

