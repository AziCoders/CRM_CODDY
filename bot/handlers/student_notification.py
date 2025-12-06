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

        # Удаляем уведомление
        del notification_storage[short_id]

    finally:
        await bot.session.close()
