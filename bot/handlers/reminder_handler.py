"""Обработчик напоминаний о посещаемости"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any
from aiogram import Bot
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from bot.services.reminder_service import ReminderService
from bot.services.role_storage import RoleStorage
from bot.services.unprocessed_students_storage import UnprocessedStudentsStorage
from bot.config import BOT_TOKEN, OWNER_ID
from bot.keyboards.payment_reminder_keyboards import (
    PaymentReminderCategoryCallback,
    PaymentReminderRefreshCallback,
    get_payment_reminder_keyboard
)
from bot.handlers.add_student import notification_storage
from bot.utils.timezone import format_datetime_str_msk, get_msk_now


class ReminderHandler:
    """Обработчик для отправки напоминаний преподавателям и менеджерам"""
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self.reminder_service = ReminderService()
        self.role_storage = RoleStorage()
        self.unprocessed_storage = UnprocessedStudentsStorage()
        self.sent_reminders = set()  # Хранит уже отправленные напоминания (teacher_user_id, group_id, date)
        self.sent_payment_reminders = set()  # Хранит уже отправленные напоминания о платежах (date_str)
        self.sent_absence_reminders = set()  # Хранит уже отправленные напоминания об отсутствиях (date_str)
        self.sent_unprocessed_reminders = set()  # Хранит уже отправленные напоминания о необработанных учениках (date_str)
    
    def _get_reminder_key(self, teacher_user_id: int, group_id: str, date_str: str) -> tuple:
        """Создает ключ для отслеживания отправленных напоминаний"""
        return (teacher_user_id, group_id, date_str)
    
    async def send_reminder(self, teacher_user_id: int, group_name: str, city: str):
        """
        Отправляет напоминание преподавателю
        
        Args:
            teacher_user_id: ID преподавателя
            group_name: Название группы
            city: Название города
        """
        message = (
            f"🔔 <b>Напоминание о посещаемости</b>\n\n"
            f"🏫 Группа: <code>{group_name}</code>\n"
            f"🏙️ Город: {city}\n\n"
            f"⚠️ Вы еще не отметили посещаемость за сегодня.\n"
            f"Пожалуйста, отметьте посещаемость через раздел 'Посещаемость' в меню."
        )
        
        try:
            await self.bot.send_message(
                chat_id=teacher_user_id,
                text=message,
                parse_mode="HTML"
            )
            print(f"✅ Напоминание отправлено преподавателю {teacher_user_id} для группы {group_name}")
        except Exception as e:
            print(f"❌ Ошибка отправки напоминания преподавателю {teacher_user_id}: {e}")
    
    async def check_and_send_reminders(self):
        """Проверяет и отправляет напоминания"""
        if not self.reminder_service.should_send_reminder_now():
            return
        
        today_str = self.reminder_service.attendance_service.format_date()
        
        # Получаем группы, которым нужно напоминание
        groups_needing_reminder = await self.reminder_service.get_groups_needing_reminder()
        
        for group_info in groups_needing_reminder:
            teacher_user_id = group_info["teacher_user_id"]
            group_id = group_info["group_id"]
            group_name = group_info["group_name"]
            city = group_info["city"]
            
            # Проверяем, не отправляли ли уже напоминание сегодня
            reminder_key = self._get_reminder_key(teacher_user_id, group_id, today_str)
            if reminder_key in self.sent_reminders:
                continue
            
            # Отправляем напоминание
            await self.send_reminder(teacher_user_id, group_name, city)
            
            # Отмечаем, что напоминание отправлено
            self.sent_reminders.add(reminder_key)
        
        # Очищаем старые записи (старше сегодняшнего дня)
        # Это нужно делать, чтобы не накапливать память
        if len(self.sent_reminders) > 1000:  # Если слишком много записей
            self.sent_reminders = {
                key for key in self.sent_reminders 
                if key[2] == today_str  # Оставляем только сегодняшние
            }
    
    async def send_payment_reminder(self):
        """Отправляет напоминания менеджерам и владельцу о предстоящих платежах"""
        # Проверяем, нужно ли отправлять напоминание сейчас (10:00 UTC)
        if not self.reminder_service.should_send_payment_reminder_now():
            return
        
        # Проверяем, не отправляли ли уже сегодня (по МСК для даты)
        today_str = format_datetime_str_msk()
        if today_str in self.sent_payment_reminders:
            return
        
        # Получаем учеников с предстоящими оплатами (сегодня, через 1, 2, 3 дня)
        students_by_days = self.reminder_service.get_students_with_upcoming_payments()
        
        # Проверяем, есть ли хоть один ученик в любом из периодов
        available_categories = [days for days in [0, 1, 2, 3] if students_by_days.get(days, [])]
        
        if not available_categories:
            # Отмечаем, что проверка была выполнена, даже если учеников нет
            self.sent_payment_reminders.add(today_str)
            return
        
        # Определяем первую категорию для отображения
        first_category = available_categories[0]
        
        # Получаем всех менеджеров и владельца
        all_users = self.role_storage.get_all_users()
        managers_and_owner = [
            user for user in all_users
            if user.get("role") in ["manager", "owner"]
        ]
        
        # Добавляем владельца, если его нет в списке
        owner_in_list = any(user.get("user_id") == OWNER_ID for user in managers_and_owner)
        if not owner_in_list:
            managers_and_owner.append({
                "user_id": OWNER_ID,
                "fio": "Владелец",
                "username": "owner",
                "role": "owner"
            })
        
        # Формируем статистику по категориям
        day_labels = {
            0: "Сегодня",
            1: "Через 1 день",
            2: "Через 2 дня",
            3: "Через 3 дня"
        }
        
        stats_lines = []
        for days in [0, 1, 2, 3]:
            count = len(students_by_days.get(days, []))
            if count > 0:
                stats_lines.append(f"{day_labels[days]}: {count} ученик(ов)")
        
        stats_text = "\n".join(stats_lines) if stats_lines else "Нет учеников"
        
        # Форматируем сообщение для первой категории
        category_text = self.reminder_service.format_payment_reminder_category(
            students_by_days, first_category
        )
        
        # Формируем полное сообщение
        full_message = (
            f"🔔 <b>Напоминание о предстоящих платежах</b>\n\n"
            f"{stats_text}\n\n"
            f"{category_text}"
        )
        
        # Отправляем уведомления с навигацией
        success_count = 0
        for user in managers_and_owner:
            user_id = user.get("user_id")
            if not user_id:
                continue
            
            try:
                # Создаем клавиатуру с навигацией
                keyboard = get_payment_reminder_keyboard(
                    current_category=first_category,
                    available_categories=available_categories,
                    message_id=0  # Будет обновлено после отправки
                )
                
                sent_message = await self.bot.send_message(
                    chat_id=user_id,
                    text=full_message,
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
                
                # Обновляем клавиатуру с правильным message_id
                keyboard_with_id = get_payment_reminder_keyboard(
                    current_category=first_category,
                    available_categories=available_categories,
                    message_id=sent_message.message_id
                )
                
                await self.bot.edit_message_reply_markup(
                    chat_id=user_id,
                    message_id=sent_message.message_id,
                    reply_markup=keyboard_with_id
                )
                
                # Закрепляем сообщение
                try:
                    await self.bot.pin_chat_message(
                        chat_id=user_id,
                        message_id=sent_message.message_id
                    )
                except Exception as pin_error:
                    print(f"⚠️ Не удалось закрепить сообщение для пользователя {user_id}: {pin_error}")
                
                success_count += 1
                print(f"✅ Напоминание о платежах отправлено пользователю {user_id} ({user.get('fio', 'N/A')})")
            except Exception as e:
                print(f"❌ Ошибка отправки напоминания о платежах пользователю {user_id}: {e}")
        
        # Отмечаем, что напоминание отправлено
        self.sent_payment_reminders.add(today_str)
        
        # Очищаем старые записи (старше недели)
        if len(self.sent_payment_reminders) > 10:
            from datetime import timedelta
            week_ago = format_datetime_str_msk(get_msk_now() - timedelta(days=7))
            self.sent_payment_reminders = {
                date_str for date_str in self.sent_payment_reminders
                if date_str >= week_ago
            }
    
    async def send_absence_reminder(self):
        """Отправляет напоминания менеджерам о учениках с двумя последними отсутствиями"""
        # Проверяем, нужно ли отправлять напоминание сейчас (10:00 UTC, в то же время, что и платежи)
        if not self.reminder_service.should_send_payment_reminder_now():
            return
        
        # Проверяем, не отправляли ли уже сегодня (по МСК для даты)
        today_str = format_datetime_str_msk()
        if today_str in self.sent_absence_reminders:
            return
        
        # Получаем учеников с двумя последними отсутствиями
        students_with_absent = self.reminder_service.get_students_with_two_absent_marks()
        
        if not students_with_absent:
            # Отмечаем, что проверка была выполнена, даже если учеников нет
            self.sent_absence_reminders.add(today_str)
            return
        
        # Получаем всех менеджеров и владельца
        all_users = self.role_storage.get_all_users()
        managers_and_owner = [
            user for user in all_users
            if user.get("role") in ["manager", "owner"]
        ]
        
        # Добавляем владельца, если его нет в списке
        owner_in_list = any(user.get("user_id") == OWNER_ID for user in managers_and_owner)
        if not owner_in_list:
            managers_and_owner.append({
                "user_id": OWNER_ID,
                "fio": "Владелец",
                "username": "owner",
                "role": "owner"
            })
        
        # Формируем сообщение
        message_lines = [
            f"🔔 <b>Напоминание об отсутствующих учениках</b>\n\n",
            f"⚠️ У следующих учеников последние 2 отметки посещаемости - <b>Отсутствовал</b>:\n\n"
        ]
        
        # Группируем по городам для удобства
        students_by_city = {}
        for student in students_with_absent:
            city = student["city"]
            if city not in students_by_city:
                students_by_city[city] = []
            students_by_city[city].append(student)
        
        # Формируем список учеников
        for city, city_students in sorted(students_by_city.items()):
            message_lines.append(f"<b>🏙️ {city}:</b>")
            for student in city_students:
                fio = student["fio"]
                group_name = student["group_name"]
                dates = student["last_two_dates"]
                message_lines.append(
                    f"• <code>{fio}</code> ({group_name})\n"
                    f"  Последние 2 отсутствия: {dates[0]}, {dates[1]}"
                )
            message_lines.append("")
        
        message_lines.append(
            "📞 <b>Пожалуйста, свяжитесь с родителями и узнайте причину отсутствия.</b>"
        )
        
        full_message = "\n".join(message_lines)
        
        # Отправляем уведомления
        success_count = 0
        for user in managers_and_owner:
            user_id = user.get("user_id")
            if not user_id:
                continue
            
            try:
                sent_message = await self.bot.send_message(
                    chat_id=user_id,
                    text=full_message,
                    parse_mode="HTML"
                )
                
                # Закрепляем сообщение
                try:
                    await self.bot.pin_chat_message(
                        chat_id=user_id,
                        message_id=sent_message.message_id
                    )
                except Exception as pin_error:
                    print(f"⚠️ Не удалось закрепить сообщение для пользователя {user_id}: {pin_error}")
                
                success_count += 1
                print(f"✅ Напоминание об отсутствиях отправлено пользователю {user_id} ({user.get('fio', 'N/A')})")
            except Exception as e:
                print(f"❌ Ошибка отправки напоминания об отсутствиях пользователю {user_id}: {e}")
        
        # Отмечаем, что напоминание отправлено
        self.sent_absence_reminders.add(today_str)
        
        # Очищаем старые записи (старше недели)
        if len(self.sent_absence_reminders) > 10:
            from datetime import timedelta
            week_ago = format_datetime_str_msk(get_msk_now() - timedelta(days=7))
            self.sent_absence_reminders = {
                date_str for date_str in self.sent_absence_reminders
                if date_str >= week_ago
            }
    
    async def send_unprocessed_students_reminder(self):
        """Отправляет ежедневные напоминания о необработанных учениках менеджерам и владельцу"""
        # Проверяем, нужно ли отправлять напоминание (каждый день в 07:00 UTC)
        if not self.reminder_service.should_send_unprocessed_students_reminder_now():
            return
        
        # Проверяем, не отправляли ли уже сегодня (по МСК для даты)
        today_str = format_datetime_str_msk()
        if today_str in self.sent_unprocessed_reminders:
            return
        
        # Получаем всех необработанных учеников
        unprocessed_students = self.unprocessed_storage.get_all_unprocessed()
        
        if not unprocessed_students:
            # Отмечаем, что проверка была выполнена, даже если учеников нет
            self.sent_unprocessed_reminders.add(today_str)
            return
        
        # Получаем всех менеджеров и владельца
        all_users = self.role_storage.get_all_users()
        managers_and_owner = [
            user for user in all_users
            if user.get("role") in ["manager", "owner"]
        ]
        
        # Добавляем владельца, если его нет в списке
        owner_in_list = any(user.get("user_id") == OWNER_ID for user in managers_and_owner)
        if not owner_in_list:
            managers_and_owner.append({
                "user_id": OWNER_ID,
                "fio": "Владелец",
                "username": "owner",
                "role": "owner"
            })
        
        # Группируем по городам
        students_by_city = {}
        for student in unprocessed_students:
            city = student.get("city_name", "Неизвестно")
            if city not in students_by_city:
                students_by_city[city] = []
            students_by_city[city].append(student)
        
        # Формируем сообщение
        message_lines = [
            f"🔔 <b>Напоминание о необработанных учениках</b>\n\n",
            f"⚠️ У вас есть <b>{len(unprocessed_students)}</b> необработанных ученик(ов):\n\n"
        ]
        
        for city, city_students in sorted(students_by_city.items()):
            message_lines.append(f"<b>🏙️ {city}:</b>")
            for student in city_students:
                student_data = student.get("student_data", {})
                group_name = student.get("group_name", "Неизвестно")
                added_time = student.get("added_time", "Неизвестно")
                fio = student_data.get("ФИО", "Не указано")
                message_lines.append(
                    f"• <code>{fio}</code> ({group_name})\n"
                    f"  Добавлен: {added_time}"
                )
            message_lines.append("")
        
        message_lines.append("📞 <b>Пожалуйста, обработайте этих учеников.</b>")
        
        full_message = "\n".join(message_lines)
        
        # Отправляем уведомления
        success_count = 0
        for user in managers_and_owner:
            user_id = user.get("user_id")
            if not user_id:
                continue
            
            try:
                sent_message = await self.bot.send_message(
                    chat_id=user_id,
                    text=full_message,
                    parse_mode="HTML"
                )
                
                # Закрепляем сообщение
                try:
                    await self.bot.pin_chat_message(
                        chat_id=user_id,
                        message_id=sent_message.message_id
                    )
                except Exception as pin_error:
                    print(f"⚠️ Не удалось закрепить сообщение для пользователя {user_id}: {pin_error}")
                
                success_count += 1
                print(f"✅ Напоминание о необработанных учениках отправлено пользователю {user_id} ({user.get('fio', 'N/A')})")
            except Exception as e:
                print(f"❌ Ошибка отправки напоминания о необработанных учениках пользователю {user_id}: {e}")
        
        # Отмечаем, что напоминание отправлено
        self.sent_unprocessed_reminders.add(today_str)
        
        # Очищаем старые записи (старше недели)
        if len(self.sent_unprocessed_reminders) > 10:
            week_ago = format_datetime_str_msk(get_msk_now() - timedelta(days=7))
            self.sent_unprocessed_reminders = {
                date_str for date_str in self.sent_unprocessed_reminders
                if date_str >= week_ago
            }
    
    async def run_reminder_loop(self):
        """Запускает цикл проверки напоминаний"""
        while True:
            try:
                await self.check_and_send_reminders()
                await self.send_payment_reminder()
                await self.send_absence_reminder()
                await self.send_unprocessed_students_reminder()
            except Exception as e:
                print(f"❌ Ошибка в цикле напоминаний: {e}")
            
            # Проверяем каждую минуту
            await asyncio.sleep(60)
