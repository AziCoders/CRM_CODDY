"""Тестовый скрипт для проверки системы напоминаний"""
import asyncio
from datetime import datetime
from bot.services.reminder_service import ReminderService
from bot.services.role_storage import RoleStorage


async def test_schedule_parsing():
    """Тест парсинга расписания"""
    print("=" * 60)
    print("ТЕСТ 1: Парсинг расписания из названий групп")
    print("=" * 60)
    
    service = ReminderService()
    
    test_groups = [
        "Назрань вт/ср 14:00",
        "Магас сб/вс 9:00",
        "Назрань пн/пт 16:00",
        "Сунжа вт/чт 17:30",
        "Назрань вт/ср 16:00",
    ]
    
    for group_name in test_groups:
        schedule = service.parse_schedule(group_name)
        if schedule:
            days, time_str = schedule
            day_names = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]
            days_str = "/".join([day_names[d] for d in days])
            print(f"✅ {group_name}")
            print(f"   → Дни: {days_str} ({days}), Время: {time_str}")
        else:
            print(f"❌ {group_name} - не удалось распарсить")
        print()
    
    print()


async def test_has_class_today():
    """Тест проверки, есть ли сегодня занятие"""
    print("=" * 60)
    print("ТЕСТ 2: Проверка, есть ли сегодня занятие")
    print("=" * 60)
    
    service = ReminderService()
    today = datetime.now()
    day_names = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
    
    print(f"Сегодня: {day_names[today.weekday()]} ({today.strftime('%d.%m.%Y')})")
    print()
    
    test_groups = [
        "Назрань вт/ср 14:00",
        "Магас сб/вс 9:00",
        "Назрань пн/пт 16:00",
        "Сунжа вт/чт 17:30",
    ]
    
    for group_name in test_groups:
        has_class = service.has_class_today(group_name)
        status = "✅ ЕСТЬ занятие" if has_class else "❌ НЕТ занятия"
        print(f"{status}: {group_name}")
    
    print()


async def test_teacher_groups():
    """Тест получения групп преподавателя"""
    print("=" * 60)
    print("ТЕСТ 3: Получение групп преподавателя")
    print("=" * 60)
    
    service = ReminderService()
    role_storage = RoleStorage()
    
    # Получаем всех преподавателей
    all_users = role_storage.get_all_users()
    teachers = [u for u in all_users if u.get("role") == "teacher"]
    
    if not teachers:
        print("❌ Преподаватели не найдены в roles.json")
        return
    
    print(f"Найдено преподавателей: {len(teachers)}\n")
    
    for teacher in teachers:
        teacher_user_id = teacher.get("user_id")
        teacher_fio = teacher.get("fio", "Не указано")
        teacher_city = teacher.get("city", "Не указан")
        
        print(f"👨‍🏫 Преподаватель: {teacher_fio}")
        print(f"   ID: {teacher_user_id}")
        print(f"   Город: {teacher_city}")
        
        groups = service.get_teacher_groups(teacher_user_id)
        print(f"   Групп: {len(groups)}")
        
        for group in groups:
            group_name = group.get("group_name", "")
            has_class = service.has_class_today(group_name)
            class_status = "✅ занятие сегодня" if has_class else "⏸ нет занятия"
            print(f"      - {group_name} ({class_status})")
        
        print()
    
    print()


async def test_attendance_check():
    """Тест проверки посещаемости"""
    print("=" * 60)
    print("ТЕСТ 4: Проверка посещаемости за сегодня")
    print("=" * 60)
    
    service = ReminderService()
    role_storage = RoleStorage()
    today_str = service.attendance_service.format_date()
    
    print(f"Проверяем посещаемость за: {today_str}\n")
    
    # Получаем всех преподавателей
    all_users = role_storage.get_all_users()
    teachers = [u for u in all_users if u.get("role") == "teacher"]
    
    if not teachers:
        print("❌ Преподаватели не найдены")
        return
    
    for teacher in teachers[:2]:  # Проверяем только первых двух для скорости
        teacher_user_id = teacher.get("user_id")
        teacher_fio = teacher.get("fio", "Не указано")
        
        groups = service.get_teacher_groups(teacher_user_id)
        
        if not groups:
            continue
        
        print(f"👨‍🏫 {teacher_fio}:")
        
        for group in groups[:3]:  # Проверяем только первые 3 группы
            group_name = group.get("group_name", "")
            city = group.get("city", "")
            group_id = group.get("group_id", "")
            
            if not service.has_class_today(group_name):
                continue
            
            print(f"   🏫 {group_name}")
            try:
                is_marked = await service.is_attendance_marked(city, group_id, today_str)
                status = "✅ ОТМЕЧЕНА" if is_marked else "❌ НЕ ОТМЕЧЕНА"
                print(f"      Посещаемость: {status}")
            except Exception as e:
                print(f"      ❌ Ошибка: {e}")
        
        print()
    
    print()


async def test_groups_needing_reminder():
    """Тест получения групп, которым нужно напоминание"""
    print("=" * 60)
    print("ТЕСТ 5: Группы, которым нужно напоминание")
    print("=" * 60)
    
    service = ReminderService()
    today_str = service.attendance_service.format_date()
    
    print(f"Дата проверки: {today_str}\n")
    
    try:
        groups = await service.get_groups_needing_reminder()
        
        if not groups:
            print("✅ Нет групп, которым нужно напоминание (все отметили посещаемость или нет занятий сегодня)")
        else:
            print(f"⚠️ Найдено групп, которым нужно напоминание: {len(groups)}\n")
            
            # Группируем по преподавателям
            by_teacher = {}
            for group in groups:
                teacher_id = group["teacher_user_id"]
                if teacher_id not in by_teacher:
                    role_storage = RoleStorage()
                    teacher_data = role_storage.get_user(teacher_id)
                    teacher_fio = teacher_data.get("fio", "Неизвестно") if teacher_data else "Неизвестно"
                    by_teacher[teacher_id] = {
                        "fio": teacher_fio,
                        "groups": []
                    }
                by_teacher[teacher_id]["groups"].append(group)
            
            for teacher_id, data in by_teacher.items():
                print(f"👨‍🏫 {data['fio']} (ID: {teacher_id}):")
                for group in data["groups"]:
                    print(f"   🏫 {group['group_name']} ({group['city']})")
                print()
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    
    print()


async def main():
    """Запуск всех тестов"""
    print("\n" + "=" * 60)
    print("ТЕСТИРОВАНИЕ СИСТЕМЫ НАПОМИНАНИЙ")
    print("=" * 60 + "\n")
    
    try:
        await test_schedule_parsing()
        await test_has_class_today()
        await test_teacher_groups()
        await test_attendance_check()
        await test_groups_needing_reminder()
        
        print("=" * 60)
        print("✅ ВСЕ ТЕСТЫ ЗАВЕРШЕНЫ")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
