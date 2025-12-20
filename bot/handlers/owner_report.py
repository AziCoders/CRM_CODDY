"""Обработчик отчета по сотрудникам для владельца"""
from aiogram import Router, F
from aiogram.types import Message
from bot.services.smm_tracking_service import SMMTrackingService
from bot.services.role_storage import RoleStorage
from datetime import datetime

router = Router()
smm_tracking = SMMTrackingService()
role_storage = RoleStorage()

# Русские названия месяцев
MONTH_NAMES = {
    1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель",
    5: "Май", 6: "Июнь", 7: "Июль", 8: "Август",
    9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь"
}


@router.message(F.text == "Отчет по сотрудникам")
async def cmd_owner_report(message: Message, user_role: str = None):
    """Обработчик кнопки 'Отчет по сотрудникам'"""
    # Проверяем права доступа
    if user_role != "owner":
        await message.answer("❌ Эта функция доступна только для владельца")
        return
    
    await message.answer("⏳ Формирую отчет...")
    
    now = datetime.now()
    current_year = now.year
    current_month = now.month
    
    # Получаем статистику по сотрудникам
    employees_stats = smm_tracking.get_all_employees_statistics(current_year, current_month)
    
    # Получаем статистику по уходу
    dropout_stats = smm_tracking.get_deleted_students_statistics(current_year, current_month)
    
    # Получаем статистику по городам
    city_stats = smm_tracking.get_city_statistics(current_year, current_month)
    
    # Получаем информацию о пользователях из role_storage
    all_users = role_storage.get_all_users()
    user_info_map = {str(user.get("user_id")): user for user in all_users}
    
    # Формируем отчет
    month_name = MONTH_NAMES.get(current_month, now.strftime('%B'))
    lines = ["📊 <b>Отчет по сотрудникам</b>\n"]
    lines.append(f"📅 Период: {month_name} {current_year}\n")
    
    # Статистика по городам
    if city_stats:
        lines.append("─" * 30)
        lines.append(f"\n🏙️ <b>Статистика по городам:</b>\n")
        
        # Сортируем города по чистому приросту (по убыванию)
        sorted_cities = sorted(
            city_stats.items(),
            key=lambda x: x[1].get("net", 0),
            reverse=True
        )
        
        for city, stats in sorted_cities:
            added = stats.get("added", 0)
            deleted = stats.get("deleted", 0)
            net = stats.get("net", 0)
            
            if net > 0:
                net_text = f"➕ {net}"
            elif net < 0:
                net_text = f"➖ {abs(net)}"
            else:
                net_text = "0"
            
            lines.append(
                f"🏙️ <b>{city}</b>:\n"
                f"   ➕ Пришло: {added} учеников\n"
                f"   ➖ Ушло: {deleted} учеников\n"
                f"   📊 Чистый прирост: {net_text} учеников"
            )
    
    # Статистика по привлеченным ученикам
    lines.append("")
    lines.append("─" * 30)
    lines.append(f"\n👥 <b>Привлеченные ученики:</b>\n")
    
    if employees_stats:
        # Сортируем по количеству привлеченных за месяц (по убыванию)
        sorted_employees = sorted(
            employees_stats.items(),
            key=lambda x: x[1].get("month", 0),
            reverse=True
        )
        
        for user_id_str, stats in sorted_employees:
            user_id = int(user_id_str)
            user_info = user_info_map.get(user_id_str, {})
            fio = user_info.get("fio", f"ID: {user_id}")
            role = stats.get("role", user_info.get("role", "unknown"))
            
            total = stats.get("total", 0)
            month = stats.get("month", 0)
            
            role_emoji = {
                "smm": "📱",
                "manager": "👨‍💼",
                "teacher": "👨‍🏫",
                "owner": "👑"
            }.get(role, "👤")
            
            lines.append(
                f"{role_emoji} <b>{fio}</b> ({role}):\n"
                f"   📅 За месяц: {month} учеников\n"
                f"   📊 За все время: {total} учеников"
            )
    else:
        lines.append("   Нет данных о привлеченных учениках")
    
    # Статистика по уходу
    lines.append("")
    lines.append("─" * 30)
    lines.append(f"\n🚪 <b>Уход учеников:</b>\n")
    
    deleted_in_month = dropout_stats.get("deleted_in_month", 0)
    total_students = dropout_stats.get("total_students", 0)
    total_deleted = dropout_stats.get("total_deleted", 0)
    dropout_rate = dropout_stats.get("dropout_rate", 0.0)
    
    lines.append(f"   📅 Ушло за месяц: {deleted_in_month} учеников")
    lines.append(f"   📊 Всего ушло: {total_deleted} учеников")
    lines.append(f"   👥 Всего учеников: {total_students}")
    
    if total_students + total_deleted > 0:
        lines.append(f"   📉 Процент ухода: {dropout_rate}%")
    
    # Уход по городам
    deleted_by_city = dropout_stats.get("deleted_by_city", {})
    if deleted_by_city:
        lines.append("")
        lines.append("   <b>Уход по городам:</b>")
        for city, count in sorted(deleted_by_city.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"      🏙️ {city}: {count} учеников")
    
    # Уход по группам
    deleted_by_group = dropout_stats.get("deleted_by_group", {})
    if deleted_by_group:
        lines.append("")
        lines.append("   <b>Уход по группам:</b>")
        # Показываем топ-10 групп
        sorted_groups = sorted(deleted_by_group.items(), key=lambda x: x[1], reverse=True)[:10]
        for group, count in sorted_groups:
            lines.append(f"      🏫 {group}: {count} учеников")
    
    # Детальный список ушедших за месяц
    deleted_list = dropout_stats.get("deleted_list", [])
    if deleted_list:
        lines.append("")
        lines.append("─" * 30)
        lines.append(f"\n📋 <b>Список ушедших за месяц:</b>\n")
        
        # Показываем первые 20 записей
        for i, student in enumerate(deleted_list[:20], 1):
            student_fio = student.get("student_fio", "Неизвестно")
            city = student.get("city_name", "Не указан")
            group = student.get("group_name", "Не указана")
            reason = student.get("deleted_reason", "Не указана")
            deleted_date = student.get("deleted_date", "")
            
            # Форматируем дату
            try:
                if deleted_date:
                    date_obj = datetime.strptime(deleted_date, "%Y-%m-%d")
                    formatted_date = date_obj.strftime("%d.%m.%Y")
                else:
                    formatted_date = "Не указана"
            except ValueError:
                formatted_date = deleted_date
            
            lines.append(
                f"{i}. <b>{student_fio}</b>\n"
                f"   🏙️ {city} | 🏫 {group}\n"
                f"   📅 {formatted_date} | 📝 {reason[:50]}"
            )
        
        if len(deleted_list) > 20:
            lines.append(f"\n... и еще {len(deleted_list) - 20} учеников")
    
    message_text = "\n".join(lines)
    
    # Разбиваем на части, если сообщение слишком длинное
    if len(message_text) > 4000:
        # Отправляем первую часть (статистика по городам)
        first_part_lines = []
        month_name = MONTH_NAMES.get(current_month, now.strftime('%B'))
        first_part_lines.append("📊 <b>Отчет по сотрудникам</b>\n")
        first_part_lines.append(f"📅 Период: {month_name} {current_year}\n")
        
        if city_stats:
            first_part_lines.append("─" * 30)
            first_part_lines.append(f"\n🏙️ <b>Статистика по городам:</b>\n")
            
            sorted_cities = sorted(
                city_stats.items(),
                key=lambda x: x[1].get("net", 0),
                reverse=True
            )
            
            for city, stats in sorted_cities:
                added = stats.get("added", 0)
                deleted = stats.get("deleted", 0)
                net = stats.get("net", 0)
                
                if net > 0:
                    net_text = f"➕ {net}"
                elif net < 0:
                    net_text = f"➖ {abs(net)}"
                else:
                    net_text = "0"
                
                first_part_lines.append(
                    f"🏙️ <b>{city}</b>:\n"
                    f"   ➕ Пришло: {added} учеников\n"
                    f"   ➖ Ушло: {deleted} учеников\n"
                    f"   📊 Чистый прирост: {net_text} учеников"
                )
        
        first_part_lines.append("")
        first_part_lines.append("─" * 30)
        first_part_lines.append(f"\n👥 <b>Привлеченные ученики:</b>\n")
        
        if employees_stats:
            sorted_employees = sorted(
                employees_stats.items(),
                key=lambda x: x[1].get("month", 0),
                reverse=True
            )
            
            for user_id_str, stats in sorted_employees:
                user_id = int(user_id_str)
                user_info = user_info_map.get(user_id_str, {})
                fio = user_info.get("fio", f"ID: {user_id}")
                role = stats.get("role", user_info.get("role", "unknown"))
                
                total = stats.get("total", 0)
                month = stats.get("month", 0)
                
                role_emoji = {
                    "smm": "📱",
                    "manager": "👨‍💼",
                    "teacher": "👨‍🏫",
                    "owner": "👑"
                }.get(role, "👤")
                
                first_part_lines.append(
                    f"{role_emoji} <b>{fio}</b> ({role}):\n"
                    f"   📅 За месяц: {month} учеников\n"
                    f"   📊 За все время: {total} учеников"
                )
        
        first_part = "\n".join(first_part_lines)
        await message.answer(first_part, parse_mode="HTML")
        
        # Отправляем вторую часть (статистика ухода)
        dropout_lines = []
        dropout_lines.append("─" * 30)
        dropout_lines.append(f"\n🚪 <b>Уход учеников:</b>\n")
        dropout_lines.append(f"   📅 Ушло за месяц: {deleted_in_month} учеников")
        dropout_lines.append(f"   📊 Всего ушло: {total_deleted} учеников")
        dropout_lines.append(f"   👥 Всего учеников: {total_students}")
        
        if total_students + total_deleted > 0:
            dropout_lines.append(f"   📉 Процент ухода: {dropout_rate}%")
        
        if deleted_by_city:
            dropout_lines.append("")
            dropout_lines.append("   <b>Уход по городам:</b>")
            for city, count in sorted(deleted_by_city.items(), key=lambda x: x[1], reverse=True):
                dropout_lines.append(f"      🏙️ {city}: {count} учеников")
        
        if deleted_by_group:
            dropout_lines.append("")
            dropout_lines.append("   <b>Уход по группам (топ-10):</b>")
            sorted_groups = sorted(deleted_by_group.items(), key=lambda x: x[1], reverse=True)[:10]
            for group, count in sorted_groups:
                dropout_lines.append(f"      🏫 {group}: {count} учеников")
        
        dropout_text = "\n".join(dropout_lines)
        await message.answer(dropout_text, parse_mode="HTML")
        
        # Отправляем третью часть (список ушедших)
        if deleted_list:
            list_lines = []
            list_lines.append("─" * 30)
            list_lines.append(f"\n📋 <b>Список ушедших за месяц:</b>\n")
            
            for i, student in enumerate(deleted_list[:15], 1):
                student_fio = student.get("student_fio", "Неизвестно")
                city = student.get("city_name", "Не указан")
                group = student.get("group_name", "Не указана")
                reason = student.get("deleted_reason", "Не указана")
                deleted_date = student.get("deleted_date", "")
                
                try:
                    if deleted_date:
                        date_obj = datetime.strptime(deleted_date, "%Y-%m-%d")
                        formatted_date = date_obj.strftime("%d.%m.%Y")
                    else:
                        formatted_date = "Не указана"
                except ValueError:
                    formatted_date = deleted_date
                
                list_lines.append(
                    f"{i}. <b>{student_fio}</b>\n"
                    f"   🏙️ {city} | 🏫 {group}\n"
                    f"   📅 {formatted_date} | 📝 {reason[:40]}"
                )
            
            if len(deleted_list) > 15:
                list_lines.append(f"\n... и еще {len(deleted_list) - 15} учеников")
            
            list_text = "\n".join(list_lines)
            await message.answer(list_text, parse_mode="HTML")
    else:
        await message.answer(message_text, parse_mode="HTML")
