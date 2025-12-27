"""Обработчик отметки посещаемости"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from typing import Dict
from bot.states.attendance_state import AttendanceState
from bot.keyboards.attendance_keyboards import (
    AttendanceCityCallback,
    AttendanceGroupCallback,
    AttendanceStudentCallback,
    AttendanceConfirmCallback,
    AttendanceBackCallback,
    get_attendance_cities_keyboard,
    get_attendance_groups_keyboard,
    get_students_keyboard
)
from bot.services.attendance_service import AttendanceService
from bot.services.group_service import GroupService
from bot.services.role_storage import RoleStorage
from bot.services.action_logger import ActionLogger
from bot.services.smm_tracking_service import SMMTrackingService
from bot.keyboards.reply_keyboards import (
    get_owner_menu,
    get_manager_menu,
    get_teacher_menu
)

router = Router()
attendance_service = AttendanceService()
group_service = GroupService()
role_storage = RoleStorage()
action_logger = ActionLogger()
smm_tracking = SMMTrackingService()


@router.message(F.text == "Посещаемость")
async def cmd_attendance(message: Message, state: FSMContext, user_role: str = None):
    """Обработчик кнопки 'Посещаемость'"""
    # Проверяем права доступа
    if user_role is None or user_role == "pending":
        await message.answer("❌ У вас нет доступа к этой функции")
        return
    
    # Проверяем доступность функции для роли
    if user_role not in ["owner", "manager", "teacher"]:
        await message.answer("❌ Отметка посещаемости доступна только для владельца, менеджера и преподавателя")
        return
    
    # Для преподавателя - сразу показываем группы его города (без кнопки "Назад")
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
        await state.update_data(selected_city=user_city, needs_back_button=False)
        await state.set_state(AttendanceState.waiting_group)
        
        # Получаем группы города
        groups = await group_service.get_city_groups(user_city)
        if not groups:
            await message.answer(f"❌ Группы не найдены для города '{user_city}'")
            await state.clear()
            return
        
        await message.answer(
            f"🏫 Отметка посещаемости\n"
            f"🏙️ Город: {user_city}\n\n"
            f"Выберите группу:",
            reply_markup=get_attendance_groups_keyboard(groups, show_back=False)
        )
        return
    
    # Для владельца и менеджера - сначала выбор города
    await message.answer(
        "🏫 Отметка посещаемости\n\n"
        "🏙️ Выберите город:",
        reply_markup=get_attendance_cities_keyboard()
    )
    await state.set_state(AttendanceState.waiting_city)


@router.callback_query(AttendanceCityCallback.filter(), AttendanceState.waiting_city)
async def process_attendance_city(
    callback: CallbackQuery,
    callback_data: AttendanceCityCallback,
    state: FSMContext
):
    """Обработка выбора города при отметке посещаемости"""
    city_name = callback_data.city
    await state.update_data(selected_city=city_name, needs_back_button=True)
    
    # Получаем группы города
    groups = await group_service.get_city_groups(city_name)
    
    if not groups:
        await callback.message.edit_text(f"❌ Группы не найдены для города '{city_name}'")
        await callback.answer("Группы не найдены", show_alert=True)
        await state.clear()
        return
    
    await callback.message.edit_text(
        f"🏫 Отметка посещаемости\n"
        f"🏙️ Город: {city_name}\n\n"
        f"Выберите группу:",
        reply_markup=get_attendance_groups_keyboard(groups, show_back=True)
    )
    await callback.answer()
    await state.set_state(AttendanceState.waiting_group)


@router.callback_query(AttendanceBackCallback.filter(), AttendanceState.waiting_group)
async def process_attendance_back(
    callback: CallbackQuery,
    state: FSMContext
):
    """Обработка кнопки 'Назад' при выборе группы - возврат к выбору города"""
    await callback.message.edit_text(
        "🏫 Отметка посещаемости\n\n"
        "🏙️ Выберите город:",
        reply_markup=get_attendance_cities_keyboard()
    )
    await callback.answer()
    await state.set_state(AttendanceState.waiting_city)


@router.callback_query(AttendanceGroupCallback.filter(), AttendanceState.waiting_group)
async def process_attendance_group(
    callback: CallbackQuery,
    callback_data: AttendanceGroupCallback,
    state: FSMContext
):
    """Обработка выбора группы при отметке посещаемости"""
    group_id = callback_data.group_id
    data = await state.get_data()
    city_name = data.get("selected_city")
    
    if not city_name:
        await callback.answer("❌ Ошибка: город не выбран", show_alert=True)
        await state.clear()
        return
    
    # Получаем название группы
    group_name = await attendance_service.get_group_name(city_name, group_id)
    if not group_name:
        await callback.answer("❌ Группа не найдена", show_alert=True)
        return
    
    # Получаем список учеников
    students = await attendance_service.get_group_students(city_name, group_id)
    
    if not students:
        await callback.answer("❌ В группе нет учеников", show_alert=True)
        return
    
    # Инициализируем статусы посещаемости (все без отметки)
    attendance_statuses = {student["ID"]: 0 for student in students}
    
    # Сохраняем данные в состояние
    await state.update_data(
        selected_group_id=group_id,
        selected_group_name=group_name,
        students=students,
        attendance_statuses=attendance_statuses
    )
    await state.set_state(AttendanceState.marking_attendance)
    
    # Создаем заголовок и клавиатуру
    header = f"🏫 Отметка посещаемости\nГруппа: {group_name}\n\n"
    header += "Варианты отметки посещаемости:\n"
    header += "✅ Присутствовал\n"
    header += "❌ Отсутствовал\n"
    header += "🟡 Опоздал\n"
    header += "🟣 Отсутствовал по причине\n\n"
    header += "Нажмите на ученика для изменения статуса:"
    
    keyboard = get_students_keyboard(students, attendance_statuses)
    
    await callback.message.edit_text(
        header,
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(AttendanceStudentCallback.filter(), AttendanceState.marking_attendance)
async def process_student_click(
    callback: CallbackQuery,
    callback_data: AttendanceStudentCallback,
    state: FSMContext
):
    """Обработка нажатия на ученика (циклическое изменение статуса)"""
    student_id = callback_data.student_id
    data = await state.get_data()
    
    students = data.get("students", [])
    attendance_statuses = data.get("attendance_statuses", {})
    
    # Циклически меняем статус: 0 -> 1 -> 2 -> 3 -> 4 -> 0
    current_status = attendance_statuses.get(student_id, 0)
    new_status = (current_status + 1) % 5
    attendance_statuses[student_id] = new_status
    
    # Обновляем состояние с новым словарем статусов
    await state.update_data(attendance_statuses=attendance_statuses.copy())
    
    # Обновляем сообщение с новой клавиатурой
    group_name = data.get("selected_group_name", "")
    header = f"🏫 Отметка посещаемости\nГруппа: {group_name}\n\n"
    header += "Варианты отметки посещаемости:\n"
    header += "✅ Присутствовал\n"
    header += "❌ Отсутствовал\n"
    header += "🟡 Опоздал\n"
    header += "🟣 Отсутствовал по причине\n\n"
    header += "Нажмите на ученика для изменения статуса:"
    
    keyboard = get_students_keyboard(students, attendance_statuses)
    
    await callback.message.edit_text(
        header,
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(AttendanceConfirmCallback.filter(), AttendanceState.marking_attendance)
async def process_attendance_confirm(
    callback: CallbackQuery,
    callback_data: AttendanceConfirmCallback,
    state: FSMContext,
    user_role: str = None
):
    """Обработка подтверждения или отмены посещаемости"""
    confirm = callback_data.confirm
    
    if not confirm:
        # Отмена
        await callback.message.edit_text("❌ Отметка посещаемости отменена")
        await callback.answer("Отменено")
        await state.clear()
        return
    
    # Подтверждение - сохраняем в Notion
    data = await state.get_data()
    city_name = data.get("selected_city")
    group_id = data.get("selected_group_id")
    group_name = data.get("selected_group_name", "")
    attendance_statuses = data.get("attendance_statuses", {})
    
    if not city_name or not group_id:
        await callback.answer("❌ Ошибка: не выбраны город или группа", show_alert=True)
        await state.clear()
        return
    
    # Фильтруем только тех, у кого есть отметка (status != 0)
    marked_attendance = {
        student_id: status
        for student_id, status in attendance_statuses.items()
        if status != 0
    }
    
    if not marked_attendance:
        await callback.answer("⚠️ Нет отмеченных учеников", show_alert=True)
        return
    
    # Показываем процесс сохранения
    await callback.message.edit_text("⏳ Сохранение посещаемости...")
    await callback.answer()
    
    # Сохраняем в Notion
    success = await attendance_service.save_attendance(
        city_name=city_name,
        group_id=group_id,
        attendance_data=marked_attendance
    )
    
    if success:
        marked_count = len(marked_attendance)
        
        # Проверяем первое посещение для учеников, привлеченных SMM
        # Отправляем уведомления только для тех, кто присутствовал (status = 1)
        from datetime import date
        today = date.today().strftime("%Y-%m-%d")
        
        for student_id, status_index in marked_attendance.items():
            if status_index == 1:  # Присутствовал
                is_first_attendance = smm_tracking.mark_first_attendance(student_id, today)
                if is_first_attendance:
                    # Получаем данные ученика для уведомления
                    student_info = smm_tracking.get_student_info(student_id)
                    if student_info:
                        await send_smm_attendance_notification(
                            student_id,
                            student_info.get("student_fio", "Неизвестно"),
                            city_name,
                            group_name
                        )
        
        # Логируем действие
        user_data = role_storage.get_user(callback.from_user.id)
        action_logger.log_action(
            user_id=callback.from_user.id,
            user_fio=user_data.get("fio", callback.from_user.full_name) if user_data else callback.from_user.full_name,
            username=callback.from_user.username or "нет",
            action_type="mark_attendance",
            action_details={
                "group_name": group_name,
                "group_id": group_id,
                "date": date.today().strftime("%d.%m.%Y"),
                "students_count": marked_count,
                "attendance_data": marked_attendance
            },
            city=city_name,
            role=user_data.get("role") if user_data else None
        )
        
        await callback.message.edit_text(
            f"✅ Посещаемость успешно сохранена!\n\n"
            f"Группа: {group_name}\n"
            f"Отмечено учеников: {marked_count}"
        )
        
        # Возвращаем меню в зависимости от роли
        if user_role == "owner":
            await callback.message.answer(
                "Выберите действие:",
                reply_markup=get_owner_menu()
            )
        elif user_role == "manager":
            await callback.message.answer(
                "Выберите действие:",
                reply_markup=get_manager_menu()
            )
        elif user_role == "teacher":
            await callback.message.answer(
                "Выберите действие:",
                reply_markup=get_teacher_menu()
            )
    else:
        await callback.message.edit_text(
            "❌ Ошибка при сохранении посещаемости.\n"
            "Пожалуйста, попробуйте снова."
        )
    
    await state.clear()


async def send_smm_attendance_notification(
    student_id: str,
    student_fio: str,
    city_name: str,
    group_name: str
):
    """Отправляет уведомление SMM о первом посещении ученика"""
    try:
        student_info = smm_tracking.get_student_info(student_id)
        if not student_info:
            return
        
        smm_user_id = student_info.get("added_by_user_id")
        if not smm_user_id:
            return
        
        from aiogram import Bot
        from bot.config import BOT_TOKEN
        
        bot = Bot(token=BOT_TOKEN)
        
        notification_text = (
            f"✅ <b>Первое посещение!</b>\n\n"
            f"👤 Ученик: {student_fio}\n"
            f"🏙️ Город: {city_name}\n"
            f"🏫 Группа: {group_name}\n\n"
            f"🎉 Ученик, которого вы привлекли, сегодня пришел на первое занятие!"
        )
        
        await bot.send_message(
            chat_id=smm_user_id,
            text=notification_text,
            parse_mode="HTML"
        )
        
        await bot.session.close()
    except Exception as e:
        print(f"❌ Ошибка отправки уведомления SMM о первом посещении: {e}")

