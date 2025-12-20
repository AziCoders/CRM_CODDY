"""Главный файл для запуска бота"""
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from bot.config import BOT_TOKEN
from bot.middlewares.role_middleware import RoleMiddleware
from bot.handlers import start, owner_role_assign, student_search, add_student, report, attendance, payment, sync, role_management, action_history, free_places, student_notification, delete_student, payment_reminder_callbacks, test_absence, info_handler, student_attendance, back_to_students, smm_report, owner_report
# payment_report_query - роутер закомментирован, импорт удален
from bot.handlers.reminder_handler import ReminderHandler
# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Главная функция запуска бота"""
    # Создаем бота и диспетчер
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # Регистрируем middleware
    dp.message.middleware(RoleMiddleware())
    dp.callback_query.middleware(RoleMiddleware())

    # Регистрируем роутеры (важен порядок - более специфичные обработчики должны быть раньше)
    dp.include_router(start.router)
    dp.include_router(owner_role_assign.router)
    dp.include_router(role_management.router)  # Управление ролями
    dp.include_router(action_history.router)  # История действий
    dp.include_router(add_student.router)  # Добавляем раньше, чтобы перехватывать кнопки меню
    dp.include_router(attendance.router)  # Посещаемость
    dp.include_router(payment.router)  # Оплата (до поиска, чтобы перехватывать запросы "Оплата")
    dp.include_router(delete_student.router)  # Удаление ученика
    dp.include_router(info_handler.router)  # Информация о городе, группах, учениках
    dp.include_router(back_to_students.router)  # Возврат к списку учеников группы
    dp.include_router(student_attendance.router)  # Просмотр посещаемости ученика
    dp.include_router(sync.router)  # Синхронизация
    dp.include_router(report.router)  # Отчеты
    dp.include_router(free_places.router)  # Свободные места
    dp.include_router(smm_report.router)  # Отчет по привлеченным для SMM
    dp.include_router(owner_report.router)  # Отчет по сотрудникам для владельца
    dp.include_router(student_notification.router)  # Уведомления о новых учениках
    dp.include_router(payment_reminder_callbacks.router)  # Обработчики callback для напоминаний о платежах
    dp.include_router(test_absence.router)  # Тестовые команды для проверки отсутствий
    # dp.include_router(payment_report_query.router)  # Запросы отчетов по оплатам через текст
    dp.include_router(student_search.router)  # Поиск должен быть последним

    logger.info("Бот запущен и готов к работе")
    
    # Создаем и запускаем обработчик напоминаний в фоне
    reminder_handler = ReminderHandler(bot)
    reminder_task = asyncio.create_task(reminder_handler.run_reminder_loop())
    logger.info("Система напоминаний запущена")

    # Запускаем polling
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        reminder_task.cancel()
        try:
            await reminder_task
        except asyncio.CancelledError:
            pass
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)



