"""Сервис для работы с группами"""
import json
from pathlib import Path
from typing import List, Dict, Any
from bot.config import ROOT_DIR, CITY_MAPPING


class GroupService:
    """Сервис для получения списка групп города"""
    
    def __init__(self):
        self.root_dir = ROOT_DIR
    
    def get_city_seats(self, city_name: str) -> int:
        """Получает количество мест в классе для города из main_page_info.json"""
        city_en = CITY_MAPPING.get(city_name, city_name)
        main_info_path = self.root_dir / f"data/{city_en}/main_page_info.json"
        
        if not main_info_path.exists():
            return 0
        
        try:
            with open(main_info_path, "r", encoding="utf-8") as f:
                info = json.load(f)
            
            seats_raw = info.get("number_seats", "")
            # Извлекаем цифры из строки
            digits = "".join(ch for ch in seats_raw if ch.isdigit())
            if digits:
                return int(digits)
            return 0
        except Exception as e:
            print(f"Ошибка загрузки main_page_info.json для {city_name}: {e}")
            return 0
    
    def get_city_groups(self, city_name: str) -> List[Dict[str, Any]]:
        """Получает список всех групп для города с количеством учеников"""
        # Преобразуем русское название в английское для пути
        city_en = CITY_MAPPING.get(city_name, city_name)
        groups_path = self.root_dir / f"data/{city_en}/groups.json"
        students_path = self.root_dir / f"data/{city_en}/students.json"
        
        if not groups_path.exists():
            return []
        
        try:
            with open(groups_path, "r", encoding="utf-8") as f:
                groups_data = json.load(f)
            
            # Загружаем данные о студентах для подсчета
            students_data = {}
            if students_path.exists():
                try:
                    with open(students_path, "r", encoding="utf-8") as f:
                        students_data = json.load(f)
                except Exception:
                    pass
            
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
        except Exception as e:
            print(f"Ошибка загрузки groups.json для {city_name}: {e}")
            return []

