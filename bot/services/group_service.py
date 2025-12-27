"""Сервис для работы с группами"""
import asyncio
from pathlib import Path
from typing import List, Dict, Any
from bot.config import ROOT_DIR, CITY_MAPPING
from bot.utils.async_file_utils import read_json_file_async


class GroupService:
    """Сервис для получения списка групп города"""
    
    def __init__(self):
        self.root_dir = ROOT_DIR
    
    async def get_city_seats(self, city_name: str) -> int:
        """Получает количество мест в классе для города из main_page_info.json (асинхронно)"""
        city_en = CITY_MAPPING.get(city_name, city_name)
        main_info_path = self.root_dir / f"data/{city_en}/main_page_info.json"
        
        info = await read_json_file_async(main_info_path)
        if not info:
            return 0
        
        seats_raw = info.get("number_seats", "")
        # Извлекаем цифры из строки
        digits = "".join(ch for ch in seats_raw if ch.isdigit())
        if digits:
            return int(digits)
        return 0
    
    async def get_city_groups(self, city_name: str) -> List[Dict[str, Any]]:
        """Получает список всех групп для города с количеством учеников (асинхронно)"""
        # Преобразуем русское название в английское для пути
        city_en = CITY_MAPPING.get(city_name, city_name)
        groups_path = self.root_dir / f"data/{city_en}/groups.json"
        students_path = self.root_dir / f"data/{city_en}/students.json"
        
        # Читаем файлы параллельно
        groups_data, students_data = await asyncio.gather(
            read_json_file_async(groups_path),
            read_json_file_async(students_path)
        )
        
        if not groups_data:
            return []
        
        groups = []
        for group_id, group_info in groups_data.items():
            # Получаем количество учеников из students.json
            total_students = 0
            if group_id in students_data:
                total_students = students_data[group_id].get("total_students", 0)
            
            groups.append({
                "group_id": group_id,
                "group_name": group_info.get("Название группы", "Без названия"),
                "city": group_info.get("Город", city_name),
                "status": group_info.get("Статус группы", ""),
                "total_students": total_students,
            })
        
        return groups
