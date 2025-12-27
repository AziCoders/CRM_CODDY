"""Сервис для работы с посещаемостью"""
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from bot.config import ROOT_DIR, CITY_MAPPING
from bot.utils.async_file_utils import read_json_file_async
from src.CRUD.crud_attendance import NotionAttendanceUpdater


class AttendanceService:
    """Сервис для работы с посещаемостью"""
    
    def __init__(self):
        self.root_dir = ROOT_DIR
        self.attendance_updater = NotionAttendanceUpdater()
    
    async def get_group_students(self, city_name: str, group_id: str) -> List[Dict[str, Any]]:
        """
        Получает список учеников группы (асинхронно)
        
        Args:
            city_name: Название города (русское)
            group_id: ID группы
            
        Returns:
            Список учеников [{"ID": "...", "ФИО": "..."}, ...]
        """
        city_en = CITY_MAPPING.get(city_name, city_name)
        students_path = self.root_dir / f"data/{city_en}/students.json"
        
        students_data = await read_json_file_async(students_path)
        if not students_data:
            return []
        
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
    
    async def get_group_name(self, city_name: str, group_id: str) -> Optional[str]:
        """Получает название группы (асинхронно)"""
        city_en = CITY_MAPPING.get(city_name, city_name)
        groups_path = self.root_dir / f"data/{city_en}/groups.json"
        
        groups_data = await read_json_file_async(groups_path)
        if not groups_data:
            return None
        
        group_info = groups_data.get(group_id, {})
        return group_info.get("Название группы", None)
    
    async def get_attendance_db_id(self, city_name: str, group_id: str) -> Optional[str]:
        """Получает ID базы данных посещаемости для группы (асинхронно)"""
        city_en = CITY_MAPPING.get(city_name, city_name)
        structure_path = self.root_dir / f"data/{city_en}/structure.json"
        
        structure_data = await read_json_file_async(structure_path)
        if not structure_data:
            return None
        
        group_info = structure_data.get(group_id, {})
        return group_info.get("attendance_db_id", None)
    
    def format_date(self, date_obj: Optional[datetime] = None) -> str:
        """
        Форматирует дату в формат дд.мм.гггг для Notion
        
        Args:
            date_obj: Объект datetime (если None, используется текущая дата)
            
        Returns:
            Строка в формате "дд.мм.гггг"
        """
        if date_obj is None:
            date_obj = datetime.now()
        
        return date_obj.strftime("%d.%m.%Y")
    
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
        attendance_db_id = await self.get_attendance_db_id(city_name, group_id)
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
