"""Сервис для работы с посещаемостью"""
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from bot.config import ROOT_DIR, CITY_MAPPING
from src.CRUD.crud_attendance import NotionAttendanceUpdater
from bot.utils.timezone import format_date_msk, get_msk_now


class AttendanceService:
    """Сервис для работы с посещаемостью"""
    
    def __init__(self):
        self.root_dir = ROOT_DIR
        self.attendance_updater = NotionAttendanceUpdater()
    
    def get_group_students(self, city_name: str, group_id: str) -> List[Dict[str, Any]]:
        """
        Получает список учеников группы
        
        Args:
            city_name: Название города (русское)
            group_id: ID группы
            
        Returns:
            Список учеников [{"ID": "...", "ФИО": "..."}, ...]
        """
        city_en = CITY_MAPPING.get(city_name, city_name)
        students_path = self.root_dir / f"data/{city_en}/students.json"
        
        if not students_path.exists():
            return []
        
        try:
            with open(students_path, "r", encoding="utf-8") as f:
                students_data = json.load(f)
            
            if group_id not in students_data:
                return []
            
            group_data = students_data[group_id]
            students_list = group_data.get("students", [])
            
            # Возвращаем только ID и ФИО
            return [
                {
                    "ID": student.get("ID", ""),
                    "ФИО": student.get("ФИО", "").strip()
                }
                for student in students_list
            ]
        except Exception as e:
            print(f"Ошибка загрузки студентов для группы {group_id}: {e}")
            return []
    
    def get_group_name(self, city_name: str, group_id: str) -> Optional[str]:
        """Получает название группы"""
        city_en = CITY_MAPPING.get(city_name, city_name)
        groups_path = self.root_dir / f"data/{city_en}/groups.json"
        
        if not groups_path.exists():
            return None
        
        try:
            with open(groups_path, "r", encoding="utf-8") as f:
                groups_data = json.load(f)
            
            group_info = groups_data.get(group_id, {})
            return group_info.get("Название группы", None)
        except Exception as e:
            print(f"Ошибка загрузки названия группы {group_id}: {e}")
            return None
    
    def get_attendance_db_id(self, city_name: str, group_id: str) -> Optional[str]:
        """Получает ID базы данных посещаемости для группы"""
        city_en = CITY_MAPPING.get(city_name, city_name)
        structure_path = self.root_dir / f"data/{city_en}/structure.json"
        
        if not structure_path.exists():
            return None
        
        try:
            with open(structure_path, "r", encoding="utf-8") as f:
                structure_data = json.load(f)
            
            group_info = structure_data.get(group_id, {})
            return group_info.get("attendance_db_id", None)
        except Exception as e:
            print(f"Ошибка загрузки attendance_db_id для группы {group_id}: {e}")
            return None
    
    def format_date(self, date_obj: Optional[datetime] = None) -> str:
        """
        Форматирует дату в формат дд.мм.гггг для Notion (по МСК)
        
        Args:
            date_obj: Объект datetime (если None, используется текущая дата МСК)
            
        Returns:
            Строка в формате "дд.мм.гггг"
        """
        return format_date_msk(date_obj)
    
    def status_index_to_notion_status(self, status_index: int) -> str:
        """
        Преобразует индекс статуса в строку для Notion
        
        Args:
            status_index: Индекс статуса (1-4)
                1 = Присутствовал
                2 = Отсутствовал
                3 = Опоздал
                4 = Отсутствовал по причине
        
        Returns:
            Строка статуса для Notion
        """
        status_map = {
            1: "Присутствовал",
            2: "Отсутствовал",
            3: "Опоздал",
            4: "Отсутствовал по причине"
        }
        return status_map.get(status_index, "Присутствовал")
    
    async def save_attendance(
        self,
        city_name: str,
        group_id: str,
        attendance_data: Dict[str, int],
        date_str: Optional[str] = None
    ) -> bool:
        """
        Сохраняет посещаемость в Notion
        
        Args:
            city_name: Название города (русское)
            group_id: ID группы
            attendance_data: Словарь {student_id: status_index}
            date_str: Дата в формате дд.мм.гггг (если None, используется текущая)
        
        Returns:
            True если успешно, False в случае ошибки
        """
        # Получаем ID базы данных посещаемости
        attendance_db_id = self.get_attendance_db_id(city_name, group_id)
        if not attendance_db_id:
            print(f"❌ Не найден attendance_db_id для группы {group_id}")
            return False
        
        # Форматируем дату
        if date_str is None:
            date_str = self.format_date()
        
        try:
            # Сохраняем посещаемость для каждого ученика
            for student_id, status_index in attendance_data.items():
                if status_index == 0:
                    # Пропускаем учеников без отметки
                    continue
                
                # Преобразуем индекс в строку статуса
                status_str = self.status_index_to_notion_status(status_index)
                
                # Сохраняем в Notion
                await self.attendance_updater.mark_attendance(
                    db_id=attendance_db_id,
                    student_id=student_id,
                    date_str=date_str,
                    status=status_str
                )
            
            return True
        except Exception as e:
            print(f"❌ Ошибка сохранения посещаемости: {e}")
            return False

