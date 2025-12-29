"""Сервис для напоминаний преподавателям о посещаемости"""
import re
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime, time, timedelta
from bot.config import ROOT_DIR, CITY_MAPPING, CITIES
from bot.services.role_storage import RoleStorage
from bot.services.attendance_service import AttendanceService
from bot.services.payment_service import PaymentService
from src.CRUD.crud_attendance import NotionAttendanceUpdater
from bot.utils.timezone import get_msk_now, get_msk_time, get_msk_date, get_utc_time


class ReminderService:
    """Сервис для отправки напоминаний преподавателям о посещаемости"""
    
    # Маппинг сокращений дней недели
    DAY_MAPPING = {
        "пн": 0,  # Понедельник
        "вт": 1,  # Вторник
        "ср": 2,  # Среда
        "чт": 3,  # Четверг
        "пт": 4,  # Пятница
        "сб": 5,  # Суббота
        "вс": 6,  # Воскресенье
    }
    
    # Время напоминаний о посещаемости (UTC)
    REMINDER_TIMES = [time(16, 0), time(17, 0), time(19, 0)]
    
    # Время напоминаний о платежах (UTC)
    PAYMENT_REMINDER_TIME = time(10, 0)
    
    # Время напоминаний о необработанных учениках (UTC)
    UNPROCESSED_STUDENTS_REMINDER_TIME = time(7, 0)
    
    def __init__(self):
        self.root_dir = ROOT_DIR
        self.role_storage = RoleStorage()
        self.attendance_service = AttendanceService()
        self.attendance_updater = NotionAttendanceUpdater()
        self.payment_service = PaymentService()
    
    def parse_schedule(self, group_name: str) -> Optional[Tuple[List[int], str]]:
        """
        Парсит расписание из названия группы
        
        Примеры:
        - "Назрань вт/ср 14:00" -> ([1, 2], "14:00")
        - "Магас сб/вс 9:00" -> ([5, 6], "09:00")
        - "Назрань пн/пт 16:00" -> ([0, 4], "16:00")
        
        Returns:
            (список дней недели, время) или None если не удалось распарсить
        """
        # Ищем паттерн: дни недели и время
        # Паттерн: два сокращения дней через / и время в формате ЧЧ:ММ
        pattern = r'([а-я]{2})/([а-я]{2})\s+(\d{1,2}):(\d{2})'
        match = re.search(pattern, group_name.lower())
        
        if not match:
            return None
        
        day1_short = match.group(1)
        day2_short = match.group(2)
        hour = int(match.group(3))
        minute = int(match.group(4))
        
        # Преобразуем дни недели
        day1 = self.DAY_MAPPING.get(day1_short)
        day2 = self.DAY_MAPPING.get(day2_short)
        
        if day1 is None or day2 is None:
            return None
        
        # Форматируем время
        time_str = f"{hour:02d}:{minute:02d}"
        
        return ([day1, day2], time_str)
    
    def has_class_today(self, group_name: str) -> bool:
        """
        Проверяет, есть ли сегодня занятие у группы
        
        Args:
            group_name: Название группы (например, "Назрань вт/ср 14:00")
            
        Returns:
            True если сегодня есть занятие, False иначе
        """
        schedule = self.parse_schedule(group_name)
        if not schedule:
            return False
        
        days, _ = schedule
        today_weekday = get_msk_now().weekday()  # 0 = понедельник, 6 = воскресенье
        
        return today_weekday in days
    
    async def is_attendance_marked(self, city_name: str, group_id: str, date_str: str) -> bool:
        """
        Проверяет, отмечена ли посещаемость за указанную дату
        
        Args:
            city_name: Название города (русское)
            group_id: ID группы
            date_str: Дата в формате дд.мм.гггг
            
        Returns:
            True если посещаемость отмечена (хотя бы для одного ученика), False иначе
        """
        attendance_db_id = self.attendance_service.get_attendance_db_id(city_name, group_id)
        if not attendance_db_id:
            return False
        
        try:
            # Получаем информацию о базе данных
            db_info = await self.attendance_updater.notion.databases.retrieve(database_id=attendance_db_id)
            props = db_info.get("properties", {})
            
            # Проверяем, есть ли столбец с этой датой
            if date_str not in props:
                return False
            
            # Запрашиваем все записи из базы
            response = await self.attendance_updater.notion.databases.query(
                database_id=attendance_db_id
            )
            
            # Проверяем, есть ли хотя бы одна запись с заполненным полем даты
            for page in response.get("results", []):
                properties = page.get("properties", {})
                date_prop = properties.get(date_str, {})
                
                # Если поле существует и заполнено (имеет select значение)
                if date_prop.get("type") == "select":
                    select_value = date_prop.get("select")
                    if select_value:  # Если есть значение (посещаемость отмечена)
                        return True
            
            return False
        except Exception as e:
            print(f"❌ Ошибка при проверке посещаемости для группы {group_id}: {e}")
            return False
    
    def get_teacher_groups(self, teacher_user_id: int) -> List[Dict]:
        """
        Получает список групп преподавателя
        
        Args:
            teacher_user_id: ID пользователя-преподавателя
            
        Returns:
            Список групп: [{"city": "...", "group_id": "...", "group_name": "..."}, ...]
        """
        user_data = self.role_storage.get_user(teacher_user_id)
        if not user_data or user_data.get("role") != "teacher":
            return []
        
        teacher_city = user_data.get("city", "")
        if not teacher_city:
            return []
        
        teacher_fio = user_data.get("fio", "").strip()
        
        city_en = CITY_MAPPING.get(teacher_city, teacher_city)
        groups_path = self.root_dir / f"data/{city_en}/groups.json"
        
        if not groups_path.exists():
            return []
        
        try:
            with open(groups_path, "r", encoding="utf-8") as f:
                groups_data = json.load(f)
            
            teacher_groups = []
            for group_id, group_info in groups_data.items():
                # Проверяем, назначен ли этот преподаватель на группу
                group_teacher = group_info.get("Преподаватель", "").strip()
                
                # Если у группы указан преподаватель, проверяем совпадение
                if group_teacher:
                    # Сравниваем по имени (может быть только имя или полное ФИО)
                    # Проверяем, содержится ли имя преподавателя группы в ФИО преподавателя из roles
                    # или наоборот
                    if (group_teacher.lower() in teacher_fio.lower() or 
                        teacher_fio.lower() in group_teacher.lower() or
                        group_teacher.lower() == teacher_fio.lower()):
                        teacher_groups.append({
                            "city": teacher_city,
                            "group_id": group_id,
                            "group_name": group_info.get("Название группы", "")
                        })
                # Если преподаватель не указан, пропускаем группу
                # Напоминания отправляются только для групп с указанным преподавателем
            
            return teacher_groups
        except Exception as e:
            print(f"❌ Ошибка загрузки групп для преподавателя {teacher_user_id}: {e}")
            return []
    
    async def get_groups_needing_reminder(self) -> List[Dict]:
        """
        Получает список групп, которым нужно отправить напоминание
        
        Returns:
            Список: [{"teacher_user_id": int, "city": str, "group_id": str, "group_name": str}, ...]
        """
        today_str = self.attendance_service.format_date()
        groups_needing_reminder = []
        
        # Получаем всех преподавателей
        all_users = self.role_storage.get_all_users()
        teachers = [u for u in all_users if u.get("role") == "teacher"]
        
        for teacher in teachers:
            teacher_user_id = teacher.get("user_id")
            teacher_groups = self.get_teacher_groups(teacher_user_id)
            
            for group in teacher_groups:
                group_name = group["group_name"]
                city_name = group["city"]
                group_id = group["group_id"]
                
                # Проверяем, есть ли сегодня занятие
                if not self.has_class_today(group_name):
                    continue
                
                # Проверяем, отмечена ли посещаемость
                is_marked = await self.is_attendance_marked(city_name, group_id, today_str)
                
                if not is_marked:
                    groups_needing_reminder.append({
                        "teacher_user_id": teacher_user_id,
                        "city": city_name,
                        "group_id": group_id,
                        "group_name": group_name
                    })
        
        return groups_needing_reminder
    
    def should_send_reminder_now(self) -> bool:
        """
        Проверяет, нужно ли отправлять напоминание сейчас (по UTC)
        
        Returns:
            True если текущее время UTC совпадает с одним из времен напоминаний
        """
        now = get_utc_time()
        
        for reminder_time in self.REMINDER_TIMES:
            # Проверяем с точностью до минуты
            if now.hour == reminder_time.hour and now.minute == reminder_time.minute:
                return True
        
        return False
    
    def should_send_payment_reminder_now(self) -> bool:
        """
        Проверяет, нужно ли отправлять напоминание о платежах сейчас (10:00 по UTC)
        
        Returns:
            True если текущее время UTC 10:00
        """
        now = get_utc_time()
        return now.hour == self.PAYMENT_REMINDER_TIME.hour and now.minute == self.PAYMENT_REMINDER_TIME.minute
    
    def should_send_unprocessed_students_reminder_now(self) -> bool:
        """
        Проверяет, нужно ли отправлять напоминание о необработанных учениках сейчас (07:00 по UTC)
        
        Returns:
            True если текущее время UTC 07:00
        """
        now = get_utc_time()
        return now.hour == self.UNPROCESSED_STUDENTS_REMINDER_TIME.hour and now.minute == self.UNPROCESSED_STUDENTS_REMINDER_TIME.minute
    
    def _parse_payment_date(self, payment_date_str: str) -> int:
        """Извлекает число из строки типа '27 числа' или '6 числа'"""
        if not payment_date_str:
            return 0
        
        # Убираем пробелы и ищем число
        match = re.search(r'(\d+)', payment_date_str)
        if match:
            return int(match.group(1))
        return 0
    
    def _should_include_student(self, payment_data: Dict[str, any], city_name: str) -> bool:
        """
        Проверяет, должен ли ученик быть включен в отчет о предстоящих платежах
        
        Args:
            payment_data: Данные об оплате ученика
            city_name: Название города
        
        Returns:
            True если ученик должен быть включен, False иначе
        """
        # Получаем статус оплаты за текущий месяц
        current_month = self.payment_service.get_current_month(city_name)
        payments_data_dict = payment_data.get("payments_data", {})
        
        if not payments_data_dict:
            # Если нет данных об оплатах, включаем ученика
            return True
        
        status = payments_data_dict.get(current_month, "")
        if isinstance(status, str):
            status = status.strip()
        else:
            status = str(status).strip() if status else ""
        
        # Исключаем если статус: "Оплатил", "Отсрочка", "Написали"
        # Включаем если статус: пусто, "Не оплатил" или нет отметки
        status_lower = status.lower()
        if status_lower in ["оплатил", "отсрочка", "написали"]:
            return False
        
        # Включаем если пусто или "Не оплатил"
        return True
    
    def _calculate_days_until_payment(self, payment_day: int, today: datetime) -> Optional[int]:
        """
        Вычисляет количество дней до ближайшей даты оплаты
        
        Args:
            payment_day: День месяца оплаты (1-31)
            today: Текущая дата
        
        Returns:
            Количество дней до оплаты (0-3) или None если оплата не в ближайшие 3 дня
        """
        if payment_day <= 0:
            return None
        
        today_date = today.date()
        current_month = today_date.month
        current_year = today_date.year
        current_day = today_date.day
        
        # Вычисляем дату оплаты в текущем месяце
        try:
            payment_date_current_month = datetime(current_year, current_month, payment_day).date()
        except ValueError:
            # Если дня нет в этом месяце (например, 31 в феврале), пропускаем
            return None
        
        # Вычисляем дату оплаты в следующем месяце
        if current_month == 12:
            next_month = 1
            next_year = current_year + 1
        else:
            next_month = current_month + 1
            next_year = current_year
        
        try:
            payment_date_next_month = datetime(next_year, next_month, payment_day).date()
        except ValueError:
            # Если дня нет в следующем месяце, пропускаем
            return None
        
        # Выбираем ближайшую дату оплаты
        if payment_date_current_month >= today_date:
            payment_date = payment_date_current_month
        else:
            payment_date = payment_date_next_month
        
        # Вычисляем разницу в днях
        days_diff = (payment_date - today_date).days
        
        # Возвращаем только если оплата в ближайшие 3 дня (0, 1, 2, 3)
        if 0 <= days_diff <= 3:
            return days_diff
        
        return None
    
    def get_students_with_upcoming_payments(self) -> Dict[int, List[Dict[str, any]]]:
        """
        Получает список всех учеников с предстоящими оплатами (сегодня, через 1, 2, 3 дня)
        
        Returns:
            Словарь {days: [students]} где days - количество дней до оплаты (0, 1, 2, 3)
        """
        students_by_days = {
            0: [],  # Сегодня
            1: [],  # Через 1 день
            2: [],  # Через 2 дня
            3: []   # Через 3 дня
        }
        
        today = get_msk_now()
        
        # Проходим по всем городам
        for city_name in CITIES:
            city_en = CITY_MAPPING.get(city_name, city_name)
            payments_path = self.root_dir / f"data/{city_en}/payments.json"
            
            if not payments_path.exists():
                continue
            
            try:
                with open(payments_path, "r", encoding="utf-8") as f:
                    payments_data = json.load(f)
                
                payments_list = payments_data.get("payments", [])
                
                # Получаем всех учеников города для получения данных
                students = self.payment_service.get_city_students(city_name)
                students_dict = {s.get("ID"): s for s in students}
                
                for payment in payments_list:
                    payment_date_str = payment.get("Дата оплаты", "")
                    if not payment_date_str:
                        continue
                    
                    # Проверяем, должен ли ученик быть включен в отчет
                    if not self._should_include_student(payment, city_name):
                        continue
                    
                    payment_day = self._parse_payment_date(payment_date_str)
                    
                    # Вычисляем количество дней до оплаты
                    days_until_payment = self._calculate_days_until_payment(payment_day, today)
                    
                    if days_until_payment is not None:
                        student_id = payment.get("student_id", "")
                        fio = payment.get("ФИО", "").strip()
                        
                        # Получаем данные ученика
                        student_data = students_dict.get(student_id, {})
                        if not student_data:
                            # Если не нашли по ID, ищем по ФИО
                            for s in students:
                                if s.get("ФИО", "").strip().lower() == fio.lower():
                                    student_data = s
                                    break
                        
                        students_by_days[days_until_payment].append({
                            "city": city_name,
                            "fio": fio,
                            "payment_date": payment_date_str,
                            "student_id": student_id,
                            "student_data": student_data,
                            "payment_data": payment
                        })
            except Exception as e:
                print(f"❌ Ошибка при обработке города {city_name}: {e}")
                continue
        
        return students_by_days
    
    def format_payment_reminder_category(
        self, 
        students_by_days: Dict[int, List[Dict[str, any]]], 
        category: int
    ) -> str:
        """
        Форматирует сообщение о предстоящих платежах для одной категории
        
        Args:
            students_by_days: Словарь {days: [students]} где days - количество дней до оплаты
            category: Категория для отображения (0-3)
            
        Returns:
            Отформатированное сообщение для категории
        """
        # Заголовки для каждого периода
        day_labels = {
            0: "Сегодня:",
            1: "Через 1 день:",
            2: "Через 2 дня:",
            3: "Через 3 дня:"
        }
        
        students = students_by_days.get(category, [])
        
        if not students:
            return f"{day_labels[category]}\nНет учеников"
        
        lines = [day_labels[category]]
        
        # Добавляем учеников этой категории
        for student_info in students:
            city = student_info["city"]
            fio = student_info["fio"]
            payment_date = student_info["payment_date"]
            student_id = student_info["student_id"]
            
            # Получаем посещаемость
            _, attendance_stats = self.payment_service.get_student_monthly_attendance(
                city, student_id, payment_date
            )
            
            # Форматируем строку посещаемости
            total_classes = attendance_stats.get("total", 0)
            present = attendance_stats.get("present", 0)
            late = attendance_stats.get("late", 0)
            absent = attendance_stats.get("absent", 0)
            absent_reason = attendance_stats.get("absent_reason", 0)
            
            attendance_str = f"{total_classes}/{present}/{late}/{absent}/{absent_reason}"
            
            # Форматируем дату оплаты (убираем "числа" если есть)
            payment_date_formatted = payment_date.replace(" числа", "")
            
            # Форматируем строку ученика
            student_line = f"<code>{city} {fio}</code> - {payment_date_formatted} {attendance_str}"
            lines.append(student_line)
        
        return "\n".join(lines)
    
    def _parse_date_field(self, date_str: str) -> Optional[datetime]:
        """
        Парсит строку даты из поля attendance.json
        
        Args:
            date_str: Строка даты в формате "дд.мм.гггг" или "дд.мм.гггг " (с пробелом)
        
        Returns:
            Объект datetime или None если не удалось распарсить
        """
        try:
            # Убираем пробелы
            date_str = date_str.strip()
            # Парсим дату
            return datetime.strptime(date_str, "%d.%m.%Y")
        except (ValueError, AttributeError):
            return None
    
    def get_students_with_two_absent_marks(self) -> List[Dict[str, any]]:
        """
        Получает список учеников, у которых последние 2 отметки посещаемости - "Отсутствовал"
        
        Returns:
            Список учеников: [{"city": str, "fio": str, "student_id": str, "group_name": str, "last_two_dates": [str, str]}, ...]
            Ученики уникальны по student_id (не дублируются)
        """
        students_with_absent = []
        seen_student_ids = set()  # Для предотвращения дубликатов
        
        # Проходим по всем городам
        for city_name in CITIES:
            city_en = CITY_MAPPING.get(city_name, city_name)
            attendance_path = self.root_dir / f"data/{city_en}/attendance.json"
            
            if not attendance_path.exists():
                continue
            
            try:
                with open(attendance_path, "r", encoding="utf-8") as f:
                    attendance_data = json.load(f)
                
                # Проходим по всем группам
                for group_id, group_info in attendance_data.items():
                    group_name = group_info.get("group_name", "")
                    attendance_records = group_info.get("attendance", [])
                    date_fields = group_info.get("fields", [])
                    
                    # Фильтруем только поля с датами (исключаем "№" и "ФИО")
                    date_fields_only = [
                        field for field in date_fields 
                        if field not in ("№", "ФИО")
                    ]
                    
                    # Парсим даты и сортируем по убыванию (самые свежие первыми)
                    parsed_dates = []
                    for date_str in date_fields_only:
                        parsed_date = self._parse_date_field(date_str)
                        if parsed_date:
                            parsed_dates.append((parsed_date, date_str))
                    
                    # Сортируем по дате (от новых к старым)
                    parsed_dates.sort(key=lambda x: x[0], reverse=True)
                    
                    # Проходим по каждому ученику
                    for record in attendance_records:
                        student_id = record.get("student_id", "")
                        fio = record.get("ФИО", "").strip()
                        attendance_dict = record.get("attendance", {})
                        
                        if not student_id or not fio:
                            continue
                        
                        # Пропускаем, если уже видели этого ученика
                        if student_id in seen_student_ids:
                            continue
                        
                        # Получаем последние 2 отметки посещаемости (по дате)
                        last_two_marks = []
                        for parsed_date, date_str in parsed_dates:
                            if date_str in attendance_dict:
                                status = attendance_dict[date_str]
                                if status:
                                    # Нормализуем статус (убираем пробелы, приводим к нижнему регистру)
                                    status_clean = str(status).strip().lower()
                                    last_two_marks.append((date_str, status_clean))
                                    
                                    # Нам нужно только последние 2 отметки
                                    if len(last_two_marks) >= 2:
                                        break
                        
                        # Проверяем, есть ли хотя бы 2 отметки
                        if len(last_two_marks) < 2:
                            continue
                        
                        # Проверяем, обе ли последние отметки - "Отсутствовал"
                        # Важно: "Отсутствовал по причине" НЕ считается как "Отсутствовал"
                        first_status = last_two_marks[0][1]  # Самая последняя отметка
                        second_status = last_two_marks[1][1]  # Предпоследняя отметка
                        
                        if first_status == "отсутствовал" and second_status == "отсутствовал":
                            students_with_absent.append({
                                "city": city_name,
                                "fio": fio,
                                "student_id": student_id,
                                "group_name": group_name,
                                "last_two_dates": [last_two_marks[0][0], last_two_marks[1][0]]
                            })
                            seen_student_ids.add(student_id)
                            
            except Exception as e:
                print(f"❌ Ошибка при обработке города {city_name}: {e}")
                continue
        
        return students_with_absent
