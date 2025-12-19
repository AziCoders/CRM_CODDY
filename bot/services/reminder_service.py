"""Сервис для напоминаний преподавателям о посещаемости"""
import re
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime, time
from bot.config import ROOT_DIR, CITY_MAPPING
from bot.services.role_storage import RoleStorage
from bot.services.attendance_service import AttendanceService
from src.CRUD.crud_attendance import NotionAttendanceUpdater


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
    
    # Время напоминаний
    REMINDER_TIMES = [time(19, 0), time(20, 0), time(22, 0)]
    
    def __init__(self):
        self.root_dir = ROOT_DIR
        self.role_storage = RoleStorage()
        self.attendance_service = AttendanceService()
        self.attendance_updater = NotionAttendanceUpdater()
    
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
        today_weekday = datetime.now().weekday()  # 0 = понедельник, 6 = воскресенье
        
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
        Проверяет, нужно ли отправлять напоминание сейчас
        
        Returns:
            True если текущее время совпадает с одним из времен напоминаний
        """
        now = datetime.now().time()
        
        for reminder_time in self.REMINDER_TIMES:
            # Проверяем с точностью до минуты
            if now.hour == reminder_time.hour and now.minute == reminder_time.minute:
                return True
        
        return False
