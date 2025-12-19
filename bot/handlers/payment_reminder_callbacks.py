"""Обработчики callback для напоминаний о платежах"""
from aiogram import Router, Bot
from aiogram.types import CallbackQuery
from bot.keyboards.payment_reminder_keyboards import (
    PaymentReminderCategoryCallback,
    PaymentReminderRefreshCallback,
    get_payment_reminder_keyboard
)
from bot.services.reminder_service import ReminderService
from bot.config import BOT_TOKEN

router = Router()
reminder_service = ReminderService()


@router.callback_query(PaymentReminderCategoryCallback.filter())
async def handle_payment_reminder_category(
    callback: CallbackQuery,
    callback_data: PaymentReminderCategoryCallback
):
    """Обработчик переключения категории напоминаний о платежах"""
    category = callback_data.category
    # Используем message_id из самого сообщения
    message_id = callback.message.message_id
    
    # Получаем актуальные данные
    students_by_days = reminder_service.get_students_with_upcoming_payments()
    
    # Определяем доступные категории
    available_categories = [days for days in [0, 1, 2, 3] if students_by_days.get(days, [])]
    
    if category not in available_categories:
        await callback.answer("❌ Категория не найдена", show_alert=True)
        return
    
    # Формируем статистику по категориям
    day_labels = {
        0: "Сегодня",
        1: "Через 1 день",
        2: "Через 2 дня",
        3: "Через 3 дня"
    }
    
    stats_lines = []
    for days in [0, 1, 2, 3]:
        count = len(students_by_days.get(days, []))
        if count > 0:
            stats_lines.append(f"{day_labels[days]}: {count} ученик(ов)")
    
    stats_text = "\n".join(stats_lines) if stats_lines else "Нет учеников"
    
    # Форматируем сообщение для выбранной категории
    category_text = reminder_service.format_payment_reminder_category(
        students_by_days, category
    )
    
    # Формируем полное сообщение
    full_message = (
        f"🔔 <b>Напоминание о предстоящих платежах</b>\n\n"
        f"{stats_text}\n\n"
        f"{category_text}"
    )
    
    # Обновляем сообщение
    try:
        await callback.message.edit_text(
            text=full_message,
            parse_mode="HTML",
            reply_markup=get_payment_reminder_keyboard(
                current_category=category,
                available_categories=available_categories,
                message_id=message_id
            )
        )
        await callback.answer()
    except Exception as e:
        print(f"❌ Ошибка обновления категории: {e}")
        await callback.answer("❌ Ошибка обновления", show_alert=True)


@router.callback_query(PaymentReminderRefreshCallback.filter())
async def handle_payment_reminder_refresh(
    callback: CallbackQuery,
    callback_data: PaymentReminderRefreshCallback
):
    """Обработчик обновления отчета о платежах"""
    # Используем message_id из самого сообщения
    message_id = callback.message.message_id
    
    # Получаем актуальные данные
    students_by_days = reminder_service.get_students_with_upcoming_payments()
    
    # Определяем доступные категории
    available_categories = [days for days in [0, 1, 2, 3] if students_by_days.get(days, [])]
    
    if not available_categories:
        # Нет данных для отображения
        try:
            await callback.message.edit_text(
                text="🔔 <b>Напоминание о предстоящих платежах</b>\n\nНет учеников с предстоящими оплатами",
                parse_mode="HTML",
                reply_markup=None
            )
            await callback.answer("✅ Обновлено")
        except Exception as e:
            print(f"❌ Ошибка обновления: {e}")
            await callback.answer("❌ Ошибка обновления", show_alert=True)
        return
    
    # Формируем статистику по категориям
    day_labels = {
        0: "Сегодня",
        1: "Через 1 день",
        2: "Через 2 дня",
        3: "Через 3 дня"
    }
    
    stats_lines = []
    for days in [0, 1, 2, 3]:
        count = len(students_by_days.get(days, []))
        if count > 0:
            stats_lines.append(f"{day_labels[days]}: {count} ученик(ов)")
    
    stats_text = "\n".join(stats_lines) if stats_lines else "Нет учеников"
    
    # Определяем первую категорию для отображения
    first_category = available_categories[0]
    
    # Форматируем сообщение для первой категории
    category_text = reminder_service.format_payment_reminder_category(
        students_by_days, first_category
    )
    
    # Формируем полное сообщение
    full_message = (
        f"🔔 <b>Напоминание о предстоящих платежах</b>\n\n"
        f"{stats_text}\n\n"
        f"{category_text}"
    )
    
    # Обновляем сообщение
    try:
        await callback.message.edit_text(
            text=full_message,
            parse_mode="HTML",
            reply_markup=get_payment_reminder_keyboard(
                current_category=first_category,
                available_categories=available_categories,
                message_id=message_id
            )
        )
        await callback.answer("✅ Отчет обновлен")
    except Exception as e:
        print(f"❌ Ошибка обновления отчета: {e}")
        await callback.answer("❌ Ошибка обновления", show_alert=True)
