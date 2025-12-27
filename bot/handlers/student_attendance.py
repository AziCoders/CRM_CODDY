"""Обработчик просмотра посещаемости ученика"""
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from aiogram import Router
from aiogram.types import CallbackQuery
from bot.keyboards.student_profile_keyboards import StudentAttendanceCallback, get_student_profile_keyboard
from bot.services.student_search import StudentSearchService
from bot.config import CITY_MAPPING, ROOT_DIR

router = Router()
search_service = StudentSearchService()


def parse_date(date_str: str) -> Optional[datetime]:
    """Парсит дату из формата дд.мм.гггг"""
    try:
        # Убираем пробелы
        date_str = date_str.strip()
        return datetime.strptime(date_str, "%d.%m.%Y")
    except:
        return None


def get_student_attendance(city_name: str, student_id: str, days: int = 30) -> Dict[str, Any]:
    """
    Получает посещаемость ученика за последние N дней
    
    Args:
        city_name: Название города (русское)
        student_id: ID ученика
        days: Количество дней для просмотра (по умолчанию 30)
    
    Returns:
        Словарь с данными посещаемости
    """
    city_en = CITY_MAPPING.get(city_name, city_name)
    attendance_path = ROOT_DIR / f"data/{city_en}/attendance.json"
    
    if not attendance_path.exists():
        return {
            "found": False,
            "message": "❌ Файл посещаемости не найден"
        }
    
    try:
        with open(attendance_path, "r", encoding="utf-8") as f:
            attendance_data = json.load(f)
        
        # Вычисляем дату начала периода
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Ищем ученика во всех группах
        student_records = []
        
        for group_id, group_info in attendance_data.items():
            attendance_records = group_info.get("attendance", [])
            date_fields = group_info.get("fields", [])[2:]  # Пропускаем № и ФИО
            
            for record in attendance_records:
                record_student_id = record.get("student_id", "")
                # Проверяем полное совпадение ID (без учета дефисов)
                record_id_no_dashes = record_student_id.replace("-", "")
                student_id_no_dashes = student_id.replace("-", "")
                
                if record_id_no_dashes == student_id_no_dashes:
                    att_data = record.get("attendance", {})
                    student_name = record.get("ФИО", "Неизвестно")
                    
                    # Фильтруем даты за последний месяц
                    filtered_attendance = {}
                    for date_str, status in att_data.items():
                        if not date_str or not date_str.strip():
                            continue
                        
                        date_obj = parse_date(date_str)
                        if date_obj and start_date <= date_obj <= end_date:
                            filtered_attendance[date_str] = status
                    
                    if filtered_attendance:
                        student_records.append({
                            "group_name": group_info.get("group_name", "Без названия"),
                            "student_name": student_name,
                            "attendance": filtered_attendance
                        })
        
        if not student_records:
            return {
                "found": False,
                "message": f"❌ Посещаемость за последние {days} дней не найдена"
            }
        
        return {
            "found": True,
            "records": student_records,
            "start_date": start_date,
            "end_date": end_date,
            "days": days
        }
    
    except Exception as e:
        print(f"Ошибка загрузки посещаемости для {city_name}: {e}")
        return {
            "found": False,
            "message": f"❌ Ошибка при загрузке посещаемости: {str(e)}"
        }


def format_attendance_message(attendance_data: Dict[str, Any]) -> str:
    """Форматирует сообщение с посещаемостью"""
    if not attendance_data.get("found"):
        return attendance_data.get("message", "❌ Данные не найдены")
    
    records = attendance_data.get("records", [])
    days = attendance_data.get("days", 30)
    
    lines = [
        f"📊 <b>Посещаемость за последние {days} дней</b>\n"
    ]
    
    # Статистика
    total_days = 0
    present_days = 0
    absent_days = 0
    
    for record in records:
        attendance = record.get("attendance", {})
        for date_str, status in attendance.items():
            total_days += 1
            status_lower = status.lower() if status else ""
            if "присутствовал" in status_lower or status == "✅":
                present_days += 1
            elif "отсутствовал" in status_lower or status == "❌":
                absent_days += 1
    
    if total_days > 0:
        present_percent = round((present_days / total_days) * 100, 1)
        lines.append(f"\n📈 <b>Статистика:</b>")
        lines.append(f"✅ Присутствовал: {present_days} ({present_percent}%)")
        lines.append(f"❌ Отсутствовал: {absent_days}")
        lines.append(f"📅 Всего занятий: {total_days}\n")
    
    # Детальная информация по группам
    for record in records:
        group_name = record.get("group_name", "Без названия")
        student_name = record.get("student_name", "Неизвестно")
        attendance = record.get("attendance", {})
        
        lines.append(f"\n🏫 <b>{group_name}</b>")
        lines.append(f"👤 {student_name}\n")
        
        # Сортируем даты
        sorted_dates = sorted(
            attendance.items(),
            key=lambda x: parse_date(x[0]) or datetime.min,
            reverse=True
        )
        
        if not sorted_dates:
            lines.append("   Нет данных за этот период")
            continue
        
        # Группируем по месяцам
        current_month = None
        month_lines = []
        
        # Словарь для перевода месяцев
        month_names_ru = {
            1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель",
            5: "Май", 6: "Июнь", 7: "Июль", 8: "Август",
            9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь"
        }
        
        for date_str, status in sorted_dates:
            date_obj = parse_date(date_str)
            if date_obj:
                month_key = date_obj.strftime("%Y-%m")
                month_name_ru = month_names_ru.get(date_obj.month, date_obj.strftime("%B"))
                month_name = f"{month_name_ru} {date_obj.year}"
                
                if month_key != current_month:
                    if month_lines:
                        lines.extend(month_lines)
                        month_lines = []
                    month_lines.append(f"\n   📅 <b>{month_name}</b>")
                    current_month = month_key
                
                # Форматируем статус
                status_lower = status.lower() if status else ""
                if "присутствовал" in status_lower or status == "✅":
                    status_emoji = "✅"
                elif "отсутствовал" in status_lower or status == "❌":
                    status_emoji = "❌"
                else:
                    status_emoji = "⚪"
                month_lines.append(f"   {status_emoji} {date_str}: {status if status else 'Не указано'}")
        
        if month_lines:
            lines.extend(month_lines)
    
    return "\n".join(lines)


@router.callback_query(StudentAttendanceCallback.filter())
async def handle_student_attendance(
    callback: CallbackQuery,
    callback_data: StudentAttendanceCallback,
    user_role: str = None
):
    """Обработка кнопки просмотра посещаемости"""
    if user_role is None or user_role == "pending":
        await callback.answer("❌ У вас нет доступа", show_alert=True)
        return
    
    student_id_short = callback_data.student_id
    city_en = callback_data.city_en
    
    # Преобразуем английское название обратно в русское
    city_name = None
    for ru_name, en_name in CITY_MAPPING.items():
        if en_name == city_en or en_name.startswith(city_en):
            city_name = ru_name
            break
    
    if not city_name:
        city_name = city_en  # Fallback
    
    # Получаем полный ID ученика
    try:
        students_data = await search_service._load_city_students(city_name)
        
        student_id = None
        group_id = None
        student_data = None
        
        for group_id_key, group_data in students_data.items():
            for student in group_data.get("students", []):
                student_id_from_data = student.get("ID", "")
                student_id_no_dashes = student_id_from_data.replace("-", "")
                # Проверяем, начинается ли ID с сокращенного значения
                if student_id_no_dashes.startswith(student_id_short):
                    student_id = student_id_from_data
                    group_id = group_id_key
                    student_data = student.copy()
                    student_data["group_name"] = group_data.get("group_name", "")
                    student_data["group_id"] = group_id
                    break
            if student_id:
                break
        
        if not student_id:
            await callback.answer("❌ Ученик не найден", show_alert=True)
            return
        
        # Получаем посещаемость
        attendance_data = get_student_attendance(city_name, student_id, days=30)
        attendance_message = format_attendance_message(attendance_data)
        
        # Показываем посещаемость
        await callback.message.answer(
            attendance_message,
            parse_mode="HTML"
        )
        
        await callback.answer()
        
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
        print(f"Ошибка при просмотре посещаемости: {e}")
