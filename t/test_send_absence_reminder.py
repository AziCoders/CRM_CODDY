"""Тестовый скрипт для ручной отправки уведомлений об отсутствиях"""
import sys
import os
import asyncio
from pathlib import Path

# Добавляем корневую директорию в путь
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from aiogram import Bot
from bot.config import BOT_TOKEN, OWNER_ID
from bot.handlers.reminder_handler import ReminderHandler


async def test_send_absence_reminder():
    """Тестирует отправку уведомлений об отсутствиях"""
    print("=" * 60)
    print("Тестирование отправки уведомлений об отсутствиях")
    print("=" * 60)
    
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN не найден в переменных окружения")
        return
    
    try:
        # Создаем бота и обработчик
        bot = Bot(token=BOT_TOKEN)
        reminder_handler = ReminderHandler(bot)
        
        print("\n📋 Проверяем наличие учеников с двумя отсутствиями...")
        
        # Получаем список учеников
        students = reminder_handler.reminder_service.get_students_with_two_absent_marks()
        
        print(f"📊 Найдено учеников: {len(students)}\n")
        
        if not students:
            print("ℹ️ Учеников с двумя последними отсутствиями не найдено.")
            print("   Уведомления не будут отправлены.")
            return
        
        # Показываем список найденных учеников
        print("📋 Список учеников для уведомления:")
        for i, student in enumerate(students, 1):
            print(f"   {i}. {student['fio']} ({student['city']}, {student['group_name']})")
        
        # Спрашиваем подтверждение
        print("\n" + "=" * 60)
        response = input("Отправить уведомления менеджерам? (да/нет): ").strip().lower()
        
        if response not in ["да", "yes", "y", "д"]:
            print("❌ Отправка отменена")
            return
        
        print("\n📤 Отправка уведомлений...\n")
        
        # Очищаем set отправленных уведомлений, чтобы можно было отправить сейчас
        reminder_handler.sent_absence_reminders.clear()
        
        # Отправляем уведомления
        await reminder_handler.send_absence_reminder()
        
        print("\n✅ Тест завершен!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Ошибка при выполнении теста: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(test_send_absence_reminder())
