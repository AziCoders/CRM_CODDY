"""Тестовый скрипт для проверки функции поиска учеников с двумя отсутствиями"""
import sys
import os
from pathlib import Path

# Добавляем корневую директорию в путь
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from bot.services.reminder_service import ReminderService


def test_get_students_with_two_absent_marks():
    """Тестирует функцию поиска учеников с двумя последними отсутствиями"""
    print("=" * 60)
    print("Тестирование функции get_students_with_two_absent_marks()")
    print("=" * 60)
    
    reminder_service = ReminderService()
    
    try:
        # Получаем список учеников с двумя отсутствиями
        students = reminder_service.get_students_with_two_absent_marks()
        
        print(f"\n✅ Функция выполнена успешно!")
        print(f"📊 Найдено учеников с двумя последними отсутствиями: {len(students)}\n")
        
        if not students:
            print("ℹ️ Учеников с двумя последними отсутствиями не найдено.")
            print("   Это может быть нормально, если все ученики посещают занятия.")
            return
        
        # Группируем по городам
        students_by_city = {}
        for student in students:
            city = student["city"]
            if city not in students_by_city:
                students_by_city[city] = []
            students_by_city[city].append(student)
        
        # Выводим результаты
        print("📋 Результаты по городам:\n")
        for city, city_students in sorted(students_by_city.items()):
            print(f"🏙️ {city}: {len(city_students)} ученик(ов)")
            for student in city_students:
                print(f"   • {student['fio']}")
                print(f"     Группа: {student['group_name']}")
                print(f"     Последние 2 отсутствия: {student['last_two_dates'][0]}, {student['last_two_dates'][1]}")
                print(f"     Student ID: {student['student_id']}")
                print()
        
        # Проверяем на дубликаты
        student_ids = [s["student_id"] for s in students]
        unique_ids = set(student_ids)
        
        if len(student_ids) != len(unique_ids):
            print("⚠️ ВНИМАНИЕ: Обнаружены дубликаты по student_id!")
            duplicates = [sid for sid in student_ids if student_ids.count(sid) > 1]
            print(f"   Дублирующиеся ID: {set(duplicates)}")
        else:
            print("✅ Проверка на дубликаты: все ученики уникальны")
        
        print("\n" + "=" * 60)
        print("Тест завершен успешно!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Ошибка при выполнении теста: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_get_students_with_two_absent_marks()
