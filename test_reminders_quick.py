"""Быстрый тест напоминаний - проверка прямо сейчас"""
import asyncio
from datetime import datetime
from bot.services.reminder_service import ReminderService
from bot.handlers.reminder_handler import ReminderHandler
from bot.services.role_storage import RoleStorage
from aiogram import Bot
from bot.config import BOT_TOKEN


async def quick_test():
    """Быстрый тест - проверяет и отправляет напоминания прямо сейчас"""
    print("=" * 60)
    print("БЫСТРЫЙ ТЕСТ СИСТЕМЫ НАПОМИНАНИЙ")
    print("=" * 60)
    print()
    
    now = datetime.now()
    print(f"Текущее время: {now.strftime('%H:%M:%S')} ({now.strftime('%d.%m.%Y')})")
    print()
    
    # Создаем бота
    bot = Bot(token=BOT_TOKEN)
    reminder_handler = ReminderHandler(bot)
    reminder_service = ReminderService()
    
    print("1. Проверяем группы, которым нужно напоминание...")
    print()
    
    try:
        # Получаем список групп, которым нужно напоминание
        groups_needing_reminder = await reminder_service.get_groups_needing_reminder()
        
        if not groups_needing_reminder:
            print("✅ Нет групп, которым нужно напоминание")
            print("   (Все группы либо не имеют занятий сегодня, либо посещаемость уже отмечена)")
        else:
            print(f"⚠️ Найдено групп без посещаемости: {len(groups_needing_reminder)}")
            print()
            
            # Группируем по преподавателям
            role_storage = RoleStorage()
            by_teacher = {}
            for group in groups_needing_reminder:
                teacher_id = group["teacher_user_id"]
                if teacher_id not in by_teacher:
                    teacher_data = role_storage.get_user(teacher_id)
                    teacher_fio = teacher_data.get("fio", "Неизвестно") if teacher_data else "Неизвестно"
                    by_teacher[teacher_id] = {
                        "fio": teacher_fio,
                        "groups": []
                    }
                by_teacher[teacher_id]["groups"].append(group)
            
            print("2. Группы, которым будет отправлено напоминание:")
            print()
            for teacher_id, data in by_teacher.items():
                print(f"   👨‍🏫 {data['fio']} (ID: {teacher_id}):")
                for group in data["groups"]:
                    print(f"      🏫 {group['group_name']} ({group['city']})")
                print()
            
            print("3. Отправка напоминаний...")
            print()
            
            # Временно меняем время, чтобы система думала, что нужно отправлять
            original_times = reminder_service.REMINDER_TIMES
            reminder_service.REMINDER_TIMES = [now.time().replace(second=0, microsecond=0)]
            
            # Принудительно проверяем и отправляем напоминания
            await reminder_handler.check_and_send_reminders()
            
            # Возвращаем оригинальное время
            reminder_service.REMINDER_TIMES = original_times
            
            print("✅ Напоминания отправлены!")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await bot.session.close()
    
    print()
    print("=" * 60)
    print("ТЕСТ ЗАВЕРШЕН")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(quick_test())
