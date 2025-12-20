"""Обработчик отчета по привлеченным ученикам для SMM"""
from aiogram import Router, F
from aiogram.types import Message
from bot.services.smm_tracking_service import SMMTrackingService
from bot.services.role_storage import RoleStorage
from datetime import datetime

router = Router()
smm_tracking = SMMTrackingService()
role_storage = RoleStorage()


@router.message(F.text == "Отчет по привлеченным")
async def cmd_smm_report(message: Message, user_role: str = None):
    """Обработчик кнопки 'Отчет по привлеченным'"""
    # Проверяем права доступа
    if user_role != "smm":
        await message.answer("❌ Эта функция доступна только для SMM")
        return
    
    await message.answer("⏳ Формирую отчет...")
    
    user_id = message.from_user.id
    
    # Получаем статистику
    stats = smm_tracking.get_statistics(user_id)
    
    # Получаем всех привлеченных учеников
    all_students = smm_tracking.get_students_by_smm(user_id)
    
    # Получаем учеников текущего месяца
    now = datetime.now()
    current_month_students = smm_tracking.get_students_by_smm_in_month(
        user_id,
        now.year,
        now.month
    )
    
    # Формируем отчет
    lines = ["📊 <b>Отчет по привлеченным ученикам</b>\n"]
    
    # Общая статистика
    lines.append("─" * 30)
    lines.append(f"\n📈 <b>Общая статистика:</b>")
    lines.append(f"   👥 Всего привлечено: {stats.get('total_students', 0)}")
    lines.append(f"   📅 В этом месяце: {stats.get('current_month_students', 0)}")
    lines.append(f"   💰 С первой оплатой: {stats.get('with_first_payment', 0)}")
    lines.append(f"   ✅ С первым посещением: {stats.get('with_first_attendance', 0)}")
    
    # Ученики текущего месяца
    if current_month_students:
        lines.append("")
        lines.append("─" * 30)
        lines.append(f"\n📅 <b>Привлечено в этом месяце ({now.strftime('%B %Y')}):</b>")
        
        for student in current_month_students:
            student_fio = student.get("student_fio", "Неизвестно")
            city_name = student.get("city_name", "Не указан")
            group_name = student.get("group_name", "Не указана")
            date_added = student.get("date_added", "")
            
            # Форматируем дату
            try:
                if date_added:
                    date_obj = datetime.strptime(date_added, "%Y-%m-%d")
                    formatted_date = date_obj.strftime("%d.%m.%Y")
                else:
                    formatted_date = "Не указана"
            except ValueError:
                formatted_date = date_added
            
            # Статусы
            payment_status = "✅" if student.get("first_payment_notified", False) else "❌"
            attendance_status = "✅" if student.get("first_attendance_notified", False) else "❌"
            
            lines.append(
                f"\n   👤 {student_fio}\n"
                f"      🏙️ {city_name} | 🏫 {group_name}\n"
                f"      📅 Добавлен: {formatted_date}\n"
                f"      💰 Оплата: {payment_status} | ✅ Посещение: {attendance_status}"
            )
    else:
        lines.append("")
        lines.append("─" * 30)
        lines.append(f"\n📅 <b>В этом месяце учеников не привлечено</b>")
    
    # Все ученики (если их не слишком много)
    if len(all_students) <= 50:
        lines.append("")
        lines.append("─" * 30)
        lines.append(f"\n👥 <b>Все привлеченные ученики:</b>")
        
        # Группируем по городам
        students_by_city = {}
        for student in all_students:
            city = student.get("city_name", "Не указан")
            if city not in students_by_city:
                students_by_city[city] = []
            students_by_city[city].append(student)
        
        for city, city_students in students_by_city.items():
            lines.append(f"\n🏙️ <b>{city}</b> ({len(city_students)}):")
            for student in city_students[:10]:  # Показываем максимум 10 на город
                student_fio = student.get("student_fio", "Неизвестно")
                payment_status = "✅" if student.get("first_payment_notified", False) else "❌"
                attendance_status = "✅" if student.get("first_attendance_notified", False) else "❌"
                lines.append(f"   • {student_fio} | 💰{payment_status} ✅{attendance_status}")
            
            if len(city_students) > 10:
                lines.append(f"   ... и еще {len(city_students) - 10} учеников")
    elif len(all_students) > 50:
        lines.append("")
        lines.append("─" * 30)
        lines.append(f"\n👥 <b>Всего привлечено: {len(all_students)} учеников</b>")
        lines.append("(Список слишком большой для отображения)")
    
    message_text = "\n".join(lines)
    
    # Разбиваем на части, если сообщение слишком длинное
    if len(message_text) > 4000:
        # Отправляем первую часть (статистика и текущий месяц)
        first_part = "\n".join(lines[:lines.index("─" * 30) + 5] if "─" * 30 in lines else lines[:20])
        await message.answer(first_part, parse_mode="HTML")
        
        # Отправляем остальные части
        remaining_lines = lines[lines.index("─" * 30) + 5:] if "─" * 30 in lines else lines[20:]
        current_message = []
        for line in remaining_lines:
            if len("\n".join(current_message) + line) > 4000:
                await message.answer("\n".join(current_message), parse_mode="HTML")
                current_message = [line]
            else:
                current_message.append(line)
        
        if current_message:
            await message.answer("\n".join(current_message), parse_mode="HTML")
    else:
        await message.answer(message_text, parse_mode="HTML")
