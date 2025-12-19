"""Тестовый скрипт для проверки напоминаний преподавателям о посещаемости"""
import sys
import os
import asyncio
from pathlib import Path
from datetime import datetime

# Добавляем корневую директорию в путь
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from bot.services.reminder_service import ReminderService
from bot.services.role_storage import RoleStorage


async def test_get_groups_needing_reminder():
    """Тестирует функцию поиска групп, которым нужно напоминание"""
    print("=" * 60)
    print("Тестирование функции get_groups_needing_reminder()")
    print("=" * 60)
    
    reminder_service = ReminderService()
    role_storage = RoleStorage()
    
    today_str = reminder_service.attendance_service.format_date()
    print(f"\n📅 Сегодняшняя дата: {today_str}")
    print(f"⏰ Текущее время: {datetime.now().strftime('%H:%M:%S')}")
    print(f"🔔 Времена напоминаний: 19:00, 20:00, 22:00\n")
    
    try:
        # Получаем всех преподавателей
        all_users = role_storage.get_all_users()
        teachers = [u for u in all_users if u.get("role") == "teacher"]
        
        print(f"👨‍🏫 Найдено преподавателей: {len(teachers)}\n")
        
        if not teachers:
            print("⚠️ В системе нет преподавателей. Добавьте их в roles.json")
            return
        
        # Показываем информацию о каждом преподавателе
        for teacher in teachers:
            teacher_id = teacher.get("user_id")
            teacher_fio = teacher.get("fio", "N/A")
            teacher_city = teacher.get("city", "N/A")
            
            print(f"👤 Преподаватель: {teacher_fio} (ID: {teacher_id}, Город: {teacher_city})")
            
            # Получаем группы преподавателя
            teacher_groups = reminder_service.get_teacher_groups(teacher_id)
            print(f"   Групп у преподавателя: {len(teacher_groups)}")
            
            for group in teacher_groups:
                group_name = group["group_name"]
                city = group["city"]
                group_id = group["group_id"]
                
                # Проверяем, есть ли сегодня занятие
                has_class = reminder_service.has_class_today(group_name)
                print(f"   • {group_name}")
                print(f"     Есть занятие сегодня: {'✅ Да' if has_class else '❌ Нет'}")
                
                if has_class:
                    # Проверяем, отмечена ли посещаемость
                    is_marked = await reminder_service.is_attendance_marked(city, group_id, today_str)
                    print(f"     Посещаемость отмечена: {'✅ Да' if is_marked else '❌ Нет'}")
                    
                    if not is_marked:
                        print(f"     ⚠️ ЭТОЙ ГРУППЕ НУЖНО НАПОМИНАНИЕ!")
                print()
        
        # Получаем список групп, которым нужно напоминание
        print("\n" + "=" * 60)
        print("Проверка групп, которым нужно напоминание...")
        print("=" * 60 + "\n")
        
        groups_needing_reminder = await reminder_service.get_groups_needing_reminder()
        
        print(f"📊 Групп, которым нужно напоминание: {len(groups_needing_reminder)}\n")
        
        if not groups_needing_reminder:
            print("✅ Все группы отметили посещаемость или сегодня нет занятий")
        else:
            print("⚠️ Группы, которым нужно напоминание:\n")
            for group_info in groups_needing_reminder:
                teacher_id = group_info["teacher_user_id"]
                teacher_data = role_storage.get_user(teacher_id)
                teacher_fio = teacher_data.get("fio", "N/A") if teacher_data else "N/A"
                
                print(f"   • {group_info['group_name']}")
                print(f"     Город: {group_info['city']}")
                print(f"     Преподаватель: {teacher_fio} (ID: {teacher_id})")
                print(f"     Group ID: {group_info['group_id']}")
                print()
        
        print("=" * 60)
        print("Тест завершен!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Ошибка при выполнении теста: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_get_groups_needing_reminder())
