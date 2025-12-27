"""Обработчик команды для тестирования напоминаний об отсутствиях"""
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from bot.config import OWNER_ID

router = Router()


@router.message(Command("test_absence"))
async def test_absence_command(message: Message, bot):
    """Команда для тестирования напоминаний об отсутствиях (только для владельца)"""
    if message.from_user.id != OWNER_ID:
        await message.answer("❌ Эта команда доступна только владельцу")
        return
    
    try:
        from bot.handlers.reminder_handler import ReminderHandler
        
        reminder_handler = ReminderHandler(bot)
        
        # Получаем список учеников для проверки
        students = await reminder_handler.reminder_service.get_students_with_two_absent_marks()
        
        if not students:
            await message.answer(
                "ℹ️ Учеников с двумя последними отсутствиями не найдено.\n\n"
                "Это может быть нормально, если все ученики посещают занятия."
            )
            return
        
        # Показываем список найденных учеников
        students_by_city = {}
        for student in students:
            city = student["city"]
            if city not in students_by_city:
                students_by_city[city] = []
            students_by_city[city].append(student)
        
        info_text = f"📊 Найдено учеников: {len(students)}\n\n"
        
        for city, city_students in sorted(students_by_city.items()):
            info_text += f"🏙️ <b>{city}:</b> {len(city_students)} ученик(ов)\n"
            for student in city_students[:5]:  # Показываем первые 5
                info_text += f"   • {student['fio']} ({student['group_name']})\n"
            if len(city_students) > 5:
                info_text += f"   ... и еще {len(city_students) - 5}\n"
            info_text += "\n"
        
        info_text += "\n📤 Отправляю уведомления менеджерам..."
        
        await message.answer(info_text, parse_mode="HTML")
        
        # Очищаем set отправленных уведомлений, чтобы можно было отправить сейчас
        reminder_handler.sent_absence_reminders.clear()
        
        # Отправляем уведомления
        await reminder_handler.send_absence_reminder()
        
        await message.answer("✅ Уведомления отправлены менеджерам и владельцу")
        
    except Exception as e:
        await message.answer(f"❌ Ошибка при выполнении команды: {e}")
        import traceback
        traceback.print_exc()


@router.message(Command("check_absence"))
async def check_absence_command(message: Message):
    """Команда для проверки учеников с отсутствиями без отправки уведомлений"""
    if message.from_user.id != OWNER_ID:
        await message.answer("❌ Эта команда доступна только владельцу")
        return
    
    try:
        from bot.services.reminder_service import ReminderService
        
        reminder_service = ReminderService()
        students = await reminder_service.get_students_with_two_absent_marks()
        
        if not students:
            await message.answer(
                "ℹ️ Учеников с двумя последними отсутствиями не найдено.\n\n"
                "Это может быть нормально, если все ученики посещают занятия."
            )
            return
        
        # Группируем по городам
        students_by_city = {}
        for student in students:
            city = student["city"]
            if city not in students_by_city:
                students_by_city[city] = []
            students_by_city[city].append(student)
        
        # Формируем сообщение
        message_text = f"📊 <b>Найдено учеников с двумя последними отсутствиями: {len(students)}</b>\n\n"
        
        for city, city_students in sorted(students_by_city.items()):
            message_text += f"🏙️ <b>{city}:</b> {len(city_students)} ученик(ов)\n"
            for student in city_students:
                message_text += (
                    f"   • <code>{student['fio']}</code>\n"
                    f"     Группа: {student['group_name']}\n"
                    f"     Даты: {student['last_two_dates'][0]}, {student['last_two_dates'][1]}\n\n"
                )
        
        # Разбиваем на части, если сообщение слишком длинное
        if len(message_text) > 4000:
            # Отправляем первую часть
            await message.answer(message_text[:4000], parse_mode="HTML")
            # Отправляем остальное
            await message.answer(message_text[4000:], parse_mode="HTML")
        else:
            await message.answer(message_text, parse_mode="HTML")
        
    except Exception as e:
        await message.answer(f"❌ Ошибка при выполнении команды: {e}")
        import traceback
        traceback.print_exc()


@router.message(Command("check_attendance_reminder"))
async def check_attendance_reminder_command(message: Message):
    """Команда для проверки групп, которым нужно напоминание о посещаемости (без отправки)"""
    if message.from_user.id != OWNER_ID:
        await message.answer("❌ Эта команда доступна только владельцу")
        return
    
    try:
        from bot.services.reminder_service import ReminderService
        from bot.services.role_storage import RoleStorage
        from datetime import datetime
        
        reminder_service = ReminderService()
        role_storage = RoleStorage()
        
        today_str = reminder_service.attendance_service.format_date()
        current_time = datetime.now().strftime('%H:%M:%S')
        
        # Получаем список групп, которым нужно напоминание
        groups_needing_reminder = await reminder_service.get_groups_needing_reminder()
        
        if not groups_needing_reminder:
            await message.answer(
                f"✅ Все группы отметили посещаемость или сегодня нет занятий\n\n"
                f"📅 Дата: {today_str}\n"
                f"⏰ Время: {current_time}\n"
                f"🔔 Времена напоминаний: 19:00, 20:00, 22:00"
            )
            return
        
        # Формируем сообщение
        message_text = (
            f"⚠️ <b>Группы, которым нужно напоминание: {len(groups_needing_reminder)}</b>\n\n"
            f"📅 Дата: {today_str}\n"
            f"⏰ Время: {current_time}\n"
            f"🔔 Времена напоминаний: 19:00, 20:00, 22:00\n\n"
        )
        
        # Группируем по преподавателям
        by_teacher = {}
        for group_info in groups_needing_reminder:
            teacher_id = group_info["teacher_user_id"]
            teacher_data = role_storage.get_user(teacher_id)
            teacher_fio = teacher_data.get("fio", "N/A") if teacher_data else f"ID: {teacher_id}"
            
            if teacher_fio not in by_teacher:
                by_teacher[teacher_fio] = []
            by_teacher[teacher_fio].append(group_info)
        
        for teacher_fio, groups in by_teacher.items():
            message_text += f"👤 <b>{teacher_fio}:</b> {len(groups)} группа(ы)\n"
            for group in groups:
                message_text += f"   • {group['group_name']} ({group['city']})\n"
            message_text += "\n"
        
        # Разбиваем на части, если сообщение слишком длинное
        if len(message_text) > 4000:
            await message.answer(message_text[:4000], parse_mode="HTML")
            await message.answer(message_text[4000:], parse_mode="HTML")
        else:
            await message.answer(message_text, parse_mode="HTML")
        
    except Exception as e:
        await message.answer(f"❌ Ошибка при выполнении команды: {e}")
        import traceback
        traceback.print_exc()


@router.message(Command("test_attendance_reminder"))
async def test_attendance_reminder_command(message: Message, bot):
    """Команда для тестирования отправки напоминаний преподавателям"""
    if message.from_user.id != OWNER_ID:
        await message.answer("❌ Эта команда доступна только владельцу")
        return
    
    try:
        from bot.handlers.reminder_handler import ReminderHandler
        from bot.services.reminder_service import ReminderService
        from bot.services.role_storage import RoleStorage
        from datetime import datetime
        
        reminder_handler = ReminderHandler(bot)
        reminder_service = ReminderService()
        role_storage = RoleStorage()
        
        today_str = reminder_service.attendance_service.format_date()
        current_time = datetime.now().strftime('%H:%M:%S')
        
        # Получаем список групп, которым нужно напоминание
        groups_needing_reminder = await reminder_service.get_groups_needing_reminder()
        
        if not groups_needing_reminder:
            await message.answer(
                f"✅ Все группы отметили посещаемость или сегодня нет занятий\n\n"
                f"📅 Дата: {today_str}\n"
                f"⏰ Время: {current_time}"
            )
            return
        
        # Показываем список групп
        info_text = (
            f"📊 <b>Найдено групп: {len(groups_needing_reminder)}</b>\n\n"
            f"📅 Дата: {today_str}\n"
            f"⏰ Время: {current_time}\n\n"
        )
        
        by_teacher = {}
        for group_info in groups_needing_reminder:
            teacher_id = group_info["teacher_user_id"]
            teacher_data = role_storage.get_user(teacher_id)
            teacher_fio = teacher_data.get("fio", "N/A") if teacher_data else f"ID: {teacher_id}"
            
            if teacher_fio not in by_teacher:
                by_teacher[teacher_fio] = []
            by_teacher[teacher_fio].append(group_info)
        
        for teacher_fio, groups in by_teacher.items():
            info_text += f"👤 <b>{teacher_fio}:</b> {len(groups)} группа(ы)\n"
            for group in groups[:3]:  # Показываем первые 3
                info_text += f"   • {group['group_name']}\n"
            if len(groups) > 3:
                info_text += f"   ... и еще {len(groups) - 3}\n"
            info_text += "\n"
        
        info_text += "\n📤 Отправляю напоминания преподавателям..."
        
        await message.answer(info_text, parse_mode="HTML")
        
        # Очищаем set отправленных напоминаний, чтобы можно было отправить сейчас
        reminder_handler.sent_reminders.clear()
        
        # Отправляем напоминания
        success_count = 0
        for group_info in groups_needing_reminder:
            teacher_user_id = group_info["teacher_user_id"]
            group_name = group_info["group_name"]
            city = group_info["city"]
            
            try:
                await reminder_handler.send_reminder(teacher_user_id, group_name, city)
                success_count += 1
            except Exception as e:
                print(f"❌ Ошибка отправки преподавателю {teacher_user_id}: {e}")
        
        await message.answer(f"✅ Напоминания отправлены {success_count} преподавателям")
        
    except Exception as e:
        await message.answer(f"❌ Ошибка при выполнении команды: {e}")
        import traceback
        traceback.print_exc()
