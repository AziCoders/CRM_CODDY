"""Обработчик уведомлений о новых учениках"""
from typing import Dict, Any
from aiogram import Router, Bot
from aiogram.types import CallbackQuery
from bot.keyboards.student_notification_keyboards import StudentProcessedCallback
from bot.config import BOT_TOKEN, OWNER_ID
from bot.services.role_storage import RoleStorage
from bot.services.unprocessed_students_storage import UnprocessedStudentsStorage
from bot.services.action_logger import ActionLogger
from datetime import datetime

router = Router()
role_storage = RoleStorage()
unprocessed_storage = UnprocessedStudentsStorage()
action_logger = ActionLogger()

# Импортируем хранилище уведомлений из add_student
from bot.handlers.add_student import notification_storage


@router.callback_query(StudentProcessedCallback.filter())
async def process_student_notification(
        callback: CallbackQuery,
        callback_data: StudentProcessedCallback
):
    """Отмечает уведомление как обработанное: обновляет текст у всех и убирает кнопку."""
    short_id = callback_data.notif
    processed_by_user = callback.from_user

    if short_id not in notification_storage:
        await callback.answer("❌ Уведомление не найдено", show_alert=True)
        return

    info = notification_storage[short_id]

    student_data = info["student_data"]
    group_name = info["group_name"]
    city_name = info["city_name"]
    messages = info["messages"]

    added_by_name = info["added_by_name"]
    added_by_username = info["added_by_username"]
    added_time = info["added_time"]

    processed_by_username = processed_by_user.username or "нет"
    processed_time = datetime.now().strftime("%d.%m.%Y %H:%M")

    # Исходный текст приходит из callback.message
    old_text = callback.message.html_text or ""

    # Если отметки "обработано" ещё нет — добавляем
    if "Ученик обработан:" not in old_text:
        updated_text = (
                old_text
                + "\n"
                + f"⏰ <b>Добавлен:</b> @{added_by_username} ({added_time})\n"
                + f"✅ <b>Ученик обработан:</b> @{processed_by_username} ({processed_time})"
        )
    else:
        updated_text = old_text  # уже обработали

    bot = Bot(token=BOT_TOKEN)

    try:
        # Обновляем у того, кто нажал
        try:
            await callback.message.edit_text(
                updated_text,
                parse_mode="HTML",
                reply_markup=None
            )
        except Exception:
            pass

        await callback.answer("✔ Отмечено как обработано")

        # Обновляем у остальных
        for msg in messages:
            user_id = msg["user_id"]
            message_id = msg["message_id"]

            if user_id == processed_by_user.id:
                continue

            try:
                await bot.edit_message_text(
                    chat_id=user_id,
                    message_id=message_id,
                    text=updated_text,
                    parse_mode="HTML",
                    reply_markup=None
                )
            except:
                pass

        # Удаляем уведомление из памяти
        del notification_storage[short_id]
        
        # Удаляем из необработанных учеников
        unprocessed_storage.remove_unprocessed_student(short_id)
        
        # Логируем действие обработки ученика
        user_data = role_storage.get_user(processed_by_user.id)
        student_id = info.get("student_id", "")
        action_logger.log_action(
            user_id=processed_by_user.id,
            user_fio=user_data.get("fio", processed_by_user.full_name) if user_data else processed_by_user.full_name,
            username=processed_by_username,
            action_type="process_student",
            action_details={
                "student": {
                    "fio": student_data.get("ФИО", "Не указано"),
                    "student_id": student_id,
                    "group_name": group_name,
                    "added_by": added_by_name,
                    "added_by_username": added_by_username,
                    "added_time": added_time
                }
            },
            city=city_name,
            role=user_data.get("role") if user_data else None
        )
        
        # Отправляем уведомления преподавателям с этого города
        await send_teacher_notifications(
            bot=bot,
            city_name=city_name,
            student_data=student_data,
            group_name=group_name
        )

    finally:
        await bot.session.close()


async def send_teacher_notifications(
    bot: Bot,
    city_name: str,
    student_data: Dict[str, Any],
    group_name: str
):
    """Отправляет уведомления преподавателям о новом обработанном ученике"""
    # Получаем всех преподавателей с этого города
    all_users = role_storage.get_all_users()
    teachers = [
        user for user in all_users
        if user.get("role") == "teacher" and user.get("city") == city_name
    ]
    
    if not teachers:
        print(f"⚠️ Преподаватели не найдены для города {city_name}")
        return
    
    print(f"👨‍🏫 Найдено преподавателей для города {city_name}: {len(teachers)}")
    
    # Формируем текст уведомления
    notification_text = (
        f"🎉 <b>Новый ученик в вашем городе</b>\n\n"
        f"👤 <b>ФИО:</b> {student_data.get('ФИО', 'Не указано')}\n"
        f"📞 <b>Номер родителя:</b> {student_data.get('Номер родителя', 'Не указано')}\n"
        f"👨‍👩‍👧 <b>Имя родителя:</b> {student_data.get('Имя родителя', 'Не указано')}\n"
        f"🎂 <b>Возраст:</b> {student_data.get('Возраст', 'Не указано')}\n"
        f"📅 <b>Дата поступления:</b> {student_data.get('Дата поступления', 'Не указано')}\n"
        f"💰 <b>Тариф:</b> {student_data.get('Тариф', 'Не указано')}\n"
        f"📊 <b>Статус:</b> {student_data.get('Статус', 'Не указано')}\n"
        f"🏫 <b>Группа:</b> {group_name}\n"
        f"🏙️ <b>Город:</b> {city_name}\n\n"
        f"✅ Ученик обработан и готов к обучению!"
    )
    
    # Отправляем уведомления всем преподавателям
    for teacher in teachers:
        user_id = teacher.get("user_id")
        if not user_id:
            continue
        
        try:
            await bot.send_message(
                chat_id=user_id,
                text=notification_text,
                parse_mode="HTML"
            )
            print(f"✅ Уведомление отправлено преподавателю {user_id} ({teacher.get('fio', 'N/A')})")
        except Exception as e:
            print(f"❌ Ошибка отправки уведомления преподавателю {user_id}: {e}")
