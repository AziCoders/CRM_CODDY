"""Тестовый скрипт для ручной отправки напоминаний преподавателям"""
import sys
import os
import asyncio
from pathlib import Path
from datetime import datetime

# Добавляем корневую директорию в путь
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from aiogram import Bot
from bot.config import BOT_TOKEN
from bot.handlers.reminder_handler import ReminderHandler
from bot.services.reminder_service import ReminderService
from bot.services.role_storage import RoleStorage


async def test_send_attendance_reminder():
    """Тестирует отправку напоминаний преподавателям"""
    print("=" * 60)
    print("Тестирование отправки напоминаний преподавателям")
    print("=" * 60)
    
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN не найден в переменных окружения")
        return
    
    try:
        # Создаем бота и обработчик
        bot = Bot(token=BOT_TOKEN)
        reminder_handler = ReminderHandler(bot)
        reminder_service = ReminderService()
        role_storage = RoleStorage()
        
        today_str = reminder_service.attendance_service.format_date()
        print(f"\n📅 Сегодняшняя дата: {today_str}")
        print(f"⏰ Текущее время: {datetime.now().strftime('%H:%M:%S')}\n")
        
        # Получаем список групп, которым нужно напоминание
        print("📋 Проверяем группы, которым нужно напоминание...\n")
        groups_needing_reminder = await reminder_service.get_groups_needing_reminder()
        
        print(f"📊 Найдено групп: {len(groups_needing_reminder)}\n")
        
        if not groups_needing_reminder:
            print("✅ Все группы отметили посещаемость или сегодня нет занятий")
            print("   Напоминания не будут отправлены.")
            return
        
        # Показываем список групп
        print("⚠️ Группы, которым нужно напоминание:\n")
        for i, group_info in enumerate(groups_needing_reminder, 1):
            teacher_id = group_info["teacher_user_id"]
            teacher_data = role_storage.get_user(teacher_id)
            teacher_fio = teacher_data.get("fio", "N/A") if teacher_data else "N/A"
            
            print(f"   {i}. {group_info['group_name']}")
            print(f"      Преподаватель: {teacher_fio} (ID: {teacher_id})")
            print(f"      Город: {group_info['city']}")
            print()
        
        # Спрашиваем подтверждение
        print("=" * 60)
        response = input("Отправить напоминания преподавателям? (да/нет): ").strip().lower()
        
        if response not in ["да", "yes", "y", "д"]:
            print("❌ Отправка отменена")
            return
        
        print("\n📤 Отправка напоминаний...\n")
        
        # Очищаем set отправленных напоминаний, чтобы можно было отправить сейчас
        reminder_handler.sent_reminders.clear()
        
        # Отправляем напоминания
        for group_info in groups_needing_reminder:
            teacher_user_id = group_info["teacher_user_id"]
            group_name = group_info["group_name"]
            city = group_info["city"]
            
            try:
                await reminder_handler.send_reminder(teacher_user_id, group_name, city)
                print(f"✅ Напоминание отправлено преподавателю {teacher_user_id} для группы {group_name}")
            except Exception as e:
                print(f"❌ Ошибка отправки преподавателю {teacher_user_id}: {e}")
        
        print("\n✅ Тест завершен!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Ошибка при выполнении теста: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(test_send_attendance_reminder())
