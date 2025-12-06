"""Главный файл для запуска VK бота"""
import asyncio
import logging
from vkbottle.bot import Bot
from vk_bot.config import VK_BOT_TOKEN
from vk_bot.handlers import start, owner_role_assign, student_search, add_student, payment_report

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Главная функция запуска бота"""
    if not VK_BOT_TOKEN:
        logger.error("❌ VK_BOT_TOKEN не установлен!")
        return

    # Создаем бота
    bot = Bot(token=VK_BOT_TOKEN)

    # Регистрируем лейблы (аналог роутеров)
    bot.labeler.load(start.labeler)
    bot.labeler.load(owner_role_assign.labeler)
    bot.labeler.load(student_search.labeler)
    bot.labeler.load(add_student.labeler)
    bot.labeler.load(payment_report.labeler)

    logger.info("VK Бот запущен и готов к работе")

    # Запускаем polling
    await bot.run_polling()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)
