"""Сервис для поиска учеников"""
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from bot.config import ROOT_DIR, CITY_MAPPING, CITIES


class StudentSearchService:
    """Сервис для поиска учеников по различным критериям"""
    
    def __init__(self):
        self.root_dir = ROOT_DIR
    
    def _load_city_students(self, city_name: str) -> Dict[str, Any]:
        """Загружает данные учеников для города"""
        # Преобразуем русское название в английское для пути
        city_en = CITY_MAPPING.get(city_name, city_name)
        students_path = self.root_dir / f"data/{city_en}/students.json"
        
        if not students_path.exists():
            return {}
        
        try:
            with open(students_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Ошибка загрузки students.json для {city_name}: {e}")
            return {}
    
    def _normalize_phone_for_search(self, phone: str) -> str:
        """Нормализует телефон для поиска"""
        if not phone:
            return ""
        digits = re.sub(r"\D", "", phone)
        if len(digits) == 11:
            if digits.startswith("8"):
                digits = "7" + digits[1:]
            if digits.startswith("7"):
                return f"+{digits}"
        return phone  # Возвращаем как есть, если не удалось нормализовать
    
    def _is_phone_number(self, query: str) -> bool:
        """Проверяет, является ли запрос номером телефона"""
        # Убираем все нецифровые символы кроме +
        digits = re.sub(r"[^\d+]", "", query)
        # Проверяем, что осталось достаточно цифр для номера
        digit_count = len(re.sub(r"[^\d]", "", digits))
        return digit_count >= 10
    
    def _is_full_name(self, query: str) -> bool:
        """Проверяет, является ли запрос полным ФИО (2+ слова)"""
        words = query.strip().split()
        return len(words) >= 2
    
    def _parse_query(self, query: str) -> Tuple[str, str]:
        """
        Определяет тип запроса и возвращает (тип, нормализованный_запрос)
        Типы: 'phone', 'full_name', 'first_name', 'last_name'
        """
        query = query.strip()
        
        if self._is_phone_number(query):
            normalized = self._normalize_phone_for_search(query)
            return ("phone", normalized)
        
        if self._is_full_name(query):
            return ("full_name", query.lower())
        
        # Одно слово - может быть имя или фамилия
        return ("name_or_surname", query.lower())
    
    def search_by_phone(self, city_name: str, phone: str) -> Optional[Dict[str, Any]]:
        """Поиск ученика по номеру телефона (полная информация)"""
        students_data = self._load_city_students(city_name)
        normalized_phone = self._normalize_phone_for_search(phone)
        
        # Также пробуем поиск без нормализации (на случай частичного совпадения)
        phone_digits = re.sub(r"\D", "", phone)
        
        for group_id, group_data in students_data.items():
            for student in group_data.get("students", []):
                student_phone = student.get("Номер родителя", "")
                if not student_phone:
                    continue
                
                # Нормализуем телефон ученика для сравнения
                student_phone_norm = self._normalize_phone_for_search(student_phone)
                student_phone_digits = re.sub(r"\D", "", student_phone)
                
                # Проверяем различные варианты совпадения
                if (student_phone_norm == normalized_phone or 
                    student_phone == phone or
                    student_phone_digits == phone_digits or
                    student_phone.endswith(phone_digits[-10:]) or  # Последние 10 цифр
                    phone_digits.endswith(re.sub(r"\D", "", student_phone)[-10:])):
                    # Добавляем информацию о группе
                    result = student.copy()
                    result["group_name"] = group_data.get("group_name", "")
                    result["group_id"] = group_id
                    result["Город"] = city_name
                    return result
        
        return None
    
    def search_by_full_name(self, city_name: str, full_name: str) -> Optional[Dict[str, Any]]:
        """Поиск ученика по полному ФИО (полная информация)"""
        students_data = self._load_city_students(city_name)
        search_name = full_name.lower().strip()
        
        for group_id, group_data in students_data.items():
            for student in group_data.get("students", []):
                student_fio = student.get("ФИО", "").lower().strip()
                if student_fio == search_name:
                    result = student.copy()
                    result["group_name"] = group_data.get("group_name", "")
                    result["group_id"] = group_id
                    result["Город"] = city_name
                    return result
        
        return None
    
    def search_by_name_or_surname(self, city_name: str, name: str) -> List[Dict[str, Any]]:
        """
        Поиск по имени или фамилии (список с краткой информацией)
        Возвращает список: номер, группа, полное ФИО
        """
        students_data = self._load_city_students(city_name)
        search_term = name.lower().strip()
        results = []
        
        for group_id, group_data in students_data.items():
            group_name = group_data.get("group_name", "")
            for student in group_data.get("students", []):
                fio = student.get("ФИО", "").strip()
                fio_lower = fio.lower()
                
                # Разбиваем ФИО на части
                fio_parts = fio_lower.split()
                
                # Проверяем, совпадает ли с именем или фамилией
                if any(part == search_term for part in fio_parts):
                    results.append({
                        "ФИО": fio,
                        "Номер родителя": student.get("Номер родителя", ""),
                        "group_name": group_name,
                        "group_id": group_id,
                        "ID": student.get("ID", ""),
                        "student_url": student.get("student_url", ""),
                        "Город": student.get("Город", city_name),
                        "Возраст": student.get("Возраст", ""),
                        "Дата поступления": student.get("Дата поступления", ""),
                        "Имя родителя": student.get("Имя родителя", ""),
                        "Тариф": student.get("Тариф", ""),
                        "Статус": student.get("Статус", ""),
                        "Ссылка на WA, TG": student.get("Ссылка на WA, TG", ""),
                        "Комментарий": student.get("Комментарий", "")
                    })
        
        return results
    
    def search(self, city_name: str, query: str) -> Tuple[str, Any]:
        """
        Универсальный поиск
        Возвращает (тип_результата, данные)
        Типы: 'full_info', 'list', 'not_found'
        """
        query_type, normalized_query = self._parse_query(query)
        
        if query_type == "phone":
            result = self.search_by_phone(city_name, normalized_query)
            if result:
                return ("full_info", result)
            return ("not_found", None)
        
        elif query_type == "full_name":
            result = self.search_by_full_name(city_name, normalized_query)
            if result:
                return ("full_info", result)
            return ("not_found", None)
        
        else:  # name_or_surname
            results = self.search_by_name_or_surname(city_name, normalized_query)
            if results:
                return ("list", results)
            return ("not_found", None)
    
    def search_all_cities(self, query: str, user_city: str = None) -> List[Dict[str, Any]]:
        """
        Поиск по всем городам (или только по городу пользователя для преподавателя)
        Возвращает список результатов с указанием города
        """
        cities_to_search = [user_city] if user_city else CITIES
        query_type, normalized_query = self._parse_query(query)
        all_results = []
        
        for city_name in cities_to_search:
            if query_type == "phone":
                result = self.search_by_phone(city_name, normalized_query)
                if result:
                    result["Город"] = city_name
                    all_results.append(result)
            elif query_type == "full_name":
                result = self.search_by_full_name(city_name, normalized_query)
                if result:
                    result["Город"] = city_name
                    all_results.append(result)
            else:  # name_or_surname
                results = self.search_by_name_or_surname(city_name, normalized_query)
                for result in results:
                    result["Город"] = city_name
                    all_results.append(result)
        
        return all_results

