"""Обработчик уведомлений о новых учениках"""
from aiogram import Router, Bot
from aiogram.types import CallbackQuery
from bot.keyboards.student_notification_keyboards import StudentProcessedCallback
from bot.config import BOT_TOKEN
from datetime import datetime

router = Router()

# Импортируем хранилище уведомлений из add_student
from bot.handlers.add_student import notification_storage


@router.callback_query(StudentProcessedCallback.filter())
async def process_student_notification(
    callback: CallbackQuery,
    callback_data: StudentProcessedCallback
):
    """Обработка кнопки 'Обработали' для уведомления о новом ученике"""
    notification_id = callback_data.notification_id
    student_id = callback_data.student_id
    processed_by_user = callback.from_user
    
    # Получаем информацию об уведомлении
    if notification_id not in add_student_module.notification_storage:
        await callback.answer("❌ Уведомление не найдено", show_alert=True)
        return
    
    notification_info = add_student_module.notification_storage[notification_id]
    messages = notification_info["messages"]
    
    # Формируем обновленный текст
    student_data = notification_info["student_data"]
    group_name = notification_info["group_name"]
    city_name = notification_info["city_name"]
    
    processed_by_name = processed_by_user.full_name or "Неизвестно"
    processed_by_username = processed_by_user.username or "нет"
    processed_time = datetime.now().strftime("%d.%m.%Y %H:%M")
    
    updated_text = (
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
        f"✅ <b>Ученик обработан:</b> @{processed_by_username} ({processed_time})"
    )
    
    bot = Bot(token=BOT_TOKEN)
    
    try:
        # Обновляем сообщение у того, кто нажал
        try:
            await callback.message.edit_text(
                updated_text,
                parse_mode="HTML"
            )
            await callback.answer("✅ Ученик отмечен как обработанный")
        except Exception as e:
            print(f"Ошибка обновления сообщения: {e}")
            await callback.answer("✅ Ученик отмечен как обработанный")
        
        # Удаляем сообщения у всех остальных
        for msg_info in messages:
            user_id = msg_info["user_id"]
            message_id = msg_info["message_id"]
            
            # Пропускаем того, кто нажал
            if user_id == processed_by_user.id:
                continue
            
            try:
                await bot.delete_message(
                    chat_id=user_id,
                    message_id=message_id
                )
            except Exception as e:
                print(f"Ошибка удаления сообщения для пользователя {user_id}: {e}")
                # Если не удалось удалить, пытаемся обновить
                try:
                    await bot.edit_message_text(
                        chat_id=user_id,
                        message_id=message_id,
                        text=updated_text,
                        parse_mode="HTML"
                    )
                except:
                    pass
        
        # Удаляем уведомление из хранилища
        if notification_id in add_student_module.notification_storage:
            del add_student_module.notification_storage[notification_id]
            
    finally:
        await bot.session.close()

