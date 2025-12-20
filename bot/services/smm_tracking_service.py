"""Сервис для отслеживания привлеченных SMM учеников"""
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from bot.config import ROOT_DIR


class SMMTrackingService:
    """Сервис для отслеживания привлеченных SMM учеников"""
    
    def __init__(self):
        self.data_dir = ROOT_DIR / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.tracking_file = self.data_dir / "smm_tracking.json"
        self._ensure_file_exists()
    
    def _ensure_file_exists(self) -> None:
        """Создает файл отслеживания если его нет"""
        if not self.tracking_file.exists():
            with open(self.tracking_file, "w", encoding="utf-8") as f:
                json.dump({}, f, ensure_ascii=False, indent=2)
    
    def _load_data(self) -> Dict[str, Any]:
        """Загружает данные отслеживания"""
        try:
            if not self.tracking_file.exists():
                return {}
            
            with open(self.tracking_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
        except Exception as e:
            print(f"⚠️ Ошибка при загрузке данных отслеживания: {e}")
            return {}
    
    def _save_data(self, data: Dict[str, Any]) -> None:
        """Сохраняет данные отслеживания"""
        try:
            # Записываем во временный файл
            temp_file = self.tracking_file.with_suffix('.tmp')
            
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            # Атомарная замена
            temp_file.replace(self.tracking_file)
        except Exception as e:
            raise RuntimeError(f"❌ Ошибка при сохранении данных отслеживания: {e}")
    
    def add_student(
        self,
        student_id: str,
        added_by_user_id: int,
        student_fio: str,
        city_name: str,
        group_name: str,
        user_role: str = "smm",
        date_added: Optional[str] = None
    ) -> None:
        """
        Добавляет ученика в отслеживание
        
        Args:
            student_id: ID ученика в Notion
            added_by_user_id: ID пользователя, который добавил ученика
            student_fio: ФИО ученика
            city_name: Название города
            group_name: Название группы
            date_added: Дата добавления (если None, используется текущая)
        """
        data = self._load_data()
        
        if date_added is None:
            date_added = datetime.now().strftime("%Y-%m-%d")
        
        data[student_id] = {
            "added_by_user_id": added_by_user_id,
            "student_fio": student_fio,
            "city_name": city_name,
            "group_name": group_name,
            "user_role": user_role,
            "date_added": date_added,
            "first_payment_notified": False,
            "first_attendance_notified": False,
            "first_payment_date": None,
            "first_attendance_date": None,
            "deleted": False,
            "deleted_date": None,
            "deleted_reason": None
        }
        
        self._save_data(data)
    
    def get_student_info(self, student_id: str) -> Optional[Dict[str, Any]]:
        """Получает информацию об ученике"""
        data = self._load_data()
        return data.get(student_id)
    
    def mark_first_payment(
        self,
        student_id: str,
        payment_date: Optional[str] = None
    ) -> bool:
        """
        Отмечает первую оплату ученика
        
        Args:
            student_id: ID ученика
            payment_date: Дата оплаты (если None, используется текущая)
        
        Returns:
            True если это первая оплата и уведомление еще не отправлялось, False иначе
        """
        data = self._load_data()
        
        if student_id not in data:
            return False
        
        student_info = data[student_id]
        
        # Если уведомление уже отправлялось, возвращаем False
        if student_info.get("first_payment_notified", False):
            return False
        
        # Отмечаем первую оплату
        if payment_date is None:
            payment_date = datetime.now().strftime("%Y-%m-%d")
        
        student_info["first_payment_notified"] = True
        student_info["first_payment_date"] = payment_date
        
        self._save_data(data)
        return True
    
    def mark_first_attendance(
        self,
        student_id: str,
        attendance_date: Optional[str] = None
    ) -> bool:
        """
        Отмечает первое посещение ученика
        
        Args:
            student_id: ID ученика
            attendance_date: Дата посещения (если None, используется текущая)
        
        Returns:
            True если это первое посещение и уведомление еще не отправлялось, False иначе
        """
        data = self._load_data()
        
        if student_id not in data:
            return False
        
        student_info = data[student_id]
        
        # Если уведомление уже отправлялось, возвращаем False
        if student_info.get("first_attendance_notified", False):
            return False
        
        # Отмечаем первое посещение
        if attendance_date is None:
            attendance_date = datetime.now().strftime("%Y-%m-%d")
        
        student_info["first_attendance_notified"] = True
        student_info["first_attendance_date"] = attendance_date
        
        self._save_data(data)
        return True
    
    def get_students_by_smm(self, smm_user_id: int) -> List[Dict[str, Any]]:
        """
        Получает список всех учеников, привлеченных указанным SMM
        
        Args:
            smm_user_id: ID SMM пользователя
        
        Returns:
            Список словарей с информацией об учениках
        """
        data = self._load_data()
        
        students = []
        for student_id, student_info in data.items():
            if student_info.get("added_by_user_id") == smm_user_id:
                students.append({
                    "student_id": student_id,
                    **student_info
                })
        
        return students
    
    def get_students_by_smm_in_month(
        self,
        smm_user_id: int,
        year: Optional[int] = None,
        month: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Получает список учеников, привлеченных SMM в указанном месяце
        
        Args:
            smm_user_id: ID SMM пользователя
            year: Год (если None, используется текущий)
            month: Месяц (1-12, если None, используется текущий)
        
        Returns:
            Список словарей с информацией об учениках
        """
        if year is None or month is None:
            now = datetime.now()
            year = year or now.year
            month = month or now.month
        
        data = self._load_data()
        
        students = []
        for student_id, student_info in data.items():
            if student_info.get("added_by_user_id") != smm_user_id:
                continue
            
            date_added = student_info.get("date_added", "")
            if not date_added:
                continue
            
            try:
                added_date = datetime.strptime(date_added, "%Y-%m-%d")
                if added_date.year == year and added_date.month == month:
                    students.append({
                        "student_id": student_id,
                        **student_info
                    })
            except ValueError:
                continue
        
        return students
    
    def get_statistics(self, smm_user_id: int) -> Dict[str, Any]:
        """
        Получает статистику по привлеченным ученикам для SMM
        
        Args:
            smm_user_id: ID SMM пользователя
        
        Returns:
            Словарь со статистикой
        """
        all_students = self.get_students_by_smm(smm_user_id)
        now = datetime.now()
        current_month_students = self.get_students_by_smm_in_month(
            smm_user_id,
            now.year,
            now.month
        )
        
        total_count = len(all_students)
        current_month_count = len(current_month_students)
        
        # Подсчитываем с первой оплатой и первым посещением
        with_first_payment = sum(
            1 for s in all_students
            if s.get("first_payment_notified", False)
        )
        with_first_attendance = sum(
            1 for s in all_students
            if s.get("first_attendance_notified", False)
        )
        
        return {
            "total_students": total_count,
            "current_month_students": current_month_count,
            "with_first_payment": with_first_payment,
            "with_first_attendance": with_first_attendance
        }
    
    def mark_deleted(
        self,
        student_id: str,
        reason: str,
        deleted_date: Optional[str] = None
    ) -> None:
        """
        Отмечает ученика как удаленного
        
        Args:
            student_id: ID ученика
            reason: Причина удаления
            deleted_date: Дата удаления (если None, используется текущая)
        """
        data = self._load_data()
        
        if student_id not in data:
            return
        
        if deleted_date is None:
            deleted_date = datetime.now().strftime("%Y-%m-%d")
        
        data[student_id]["deleted"] = True
        data[student_id]["deleted_date"] = deleted_date
        data[student_id]["deleted_reason"] = reason
        
        self._save_data(data)
    
    def get_all_employees_statistics(
        self,
        year: Optional[int] = None,
        month: Optional[int] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Получает статистику по всем сотрудникам
        
        Args:
            year: Год (если None, используется текущий)
            month: Месяц (1-12, если None, используется текущий)
        
        Returns:
            Словарь {user_id: {"fio": ..., "total": ..., "month": ..., "role": ...}}
        """
        if year is None or month is None:
            now = datetime.now()
            year = year or now.year
            month = month or now.month
        
        data = self._load_data()
        
        employees_stats = {}
        
        for student_id, student_info in data.items():
            # Пропускаем удаленных учеников при подсчете привлеченных
            if student_info.get("deleted", False):
                continue
            
            user_id = student_info.get("added_by_user_id")
            if not user_id:
                continue
            
            if user_id not in employees_stats:
                employees_stats[user_id] = {
                    "user_id": user_id,
                    "fio": None,  # Будет заполнено из role_storage
                    "role": student_info.get("user_role", "unknown"),
                    "total": 0,
                    "month": 0
                }
            
            # Подсчитываем общее количество
            employees_stats[user_id]["total"] += 1
            
            # Подсчитываем за месяц
            date_added = student_info.get("date_added", "")
            if date_added:
                try:
                    added_date = datetime.strptime(date_added, "%Y-%m-%d")
                    if added_date.year == year and added_date.month == month:
                        employees_stats[user_id]["month"] += 1
                except ValueError:
                    pass
        
        return employees_stats
    
    def get_city_statistics(
        self,
        year: Optional[int] = None,
        month: Optional[int] = None
    ) -> Dict[str, Dict[str, int]]:
        """
        Получает статистику по городам (сколько пришло и ушло)
        
        Args:
            year: Год (если None, используется текущий)
            month: Месяц (1-12, если None, используется текущий)
        
        Returns:
            Словарь {city_name: {"added": ..., "deleted": ..., "net": ...}}
        """
        if year is None or month is None:
            now = datetime.now()
            year = year or now.year
            month = month or now.month
        
        data = self._load_data()
        
        city_stats = {}
        
        for student_id, student_info in data.items():
            city = student_info.get("city_name", "Не указан")
            
            if city not in city_stats:
                city_stats[city] = {
                    "added": 0,
                    "deleted": 0,
                    "net": 0
                }
            
            # Подсчитываем пришедших за месяц
            if not student_info.get("deleted", False):
                date_added = student_info.get("date_added", "")
                if date_added:
                    try:
                        added_date = datetime.strptime(date_added, "%Y-%m-%d")
                        if added_date.year == year and added_date.month == month:
                            city_stats[city]["added"] += 1
                    except ValueError:
                        pass
            
            # Подсчитываем ушедших за месяц
            if student_info.get("deleted", False):
                deleted_date = student_info.get("deleted_date", "")
                if deleted_date:
                    try:
                        deleted_date_obj = datetime.strptime(deleted_date, "%Y-%m-%d")
                        if deleted_date_obj.year == year and deleted_date_obj.month == month:
                            city_stats[city]["deleted"] += 1
                    except ValueError:
                        pass
        
        # Вычисляем чистый прирост для каждого города
        for city in city_stats:
            city_stats[city]["net"] = city_stats[city]["added"] - city_stats[city]["deleted"]
        
        return city_stats
    
    def get_deleted_students_statistics(
        self,
        year: Optional[int] = None,
        month: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Получает статистику по удаленным ученикам
        
        Args:
            year: Год (если None, используется текущий)
            month: Месяц (1-12, если None, используется текущий)
        
        Returns:
            Словарь со статистикой ухода
        """
        if year is None or month is None:
            now = datetime.now()
            year = year or now.year
            month = month or now.month
        
        data = self._load_data()
        
        deleted_in_month = []
        deleted_by_city = {}
        deleted_by_group = {}
        
        total_students = len([s for s in data.values() if not s.get("deleted", False)])
        total_deleted = len([s for s in data.values() if s.get("deleted", False)])
        
        for student_id, student_info in data.items():
            if not student_info.get("deleted", False):
                continue
            
            deleted_date = student_info.get("deleted_date", "")
            if not deleted_date:
                continue
            
            try:
                deleted_date_obj = datetime.strptime(deleted_date, "%Y-%m-%d")
                if deleted_date_obj.year == year and deleted_date_obj.month == month:
                    city = student_info.get("city_name", "Не указан")
                    group = student_info.get("group_name", "Не указана")
                    
                    deleted_in_month.append({
                        "student_id": student_id,
                        "student_fio": student_info.get("student_fio", "Неизвестно"),
                        "city_name": city,
                        "group_name": group,
                        "deleted_date": deleted_date,
                        "deleted_reason": student_info.get("deleted_reason", "")
                    })
                    
                    # Подсчитываем по городам
                    if city not in deleted_by_city:
                        deleted_by_city[city] = 0
                    deleted_by_city[city] += 1
                    
                    # Подсчитываем по группам
                    group_key = f"{city} - {group}"
                    if group_key not in deleted_by_group:
                        deleted_by_group[group_key] = 0
                    deleted_by_group[group_key] += 1
            except ValueError:
                continue
        
        # Вычисляем процент ухода
        dropout_rate = 0.0
        if total_students + total_deleted > 0:
            dropout_rate = (total_deleted / (total_students + total_deleted)) * 100
        
        return {
            "deleted_in_month": len(deleted_in_month),
            "deleted_list": deleted_in_month,
            "deleted_by_city": deleted_by_city,
            "deleted_by_group": deleted_by_group,
            "total_students": total_students,
            "total_deleted": total_deleted,
            "dropout_rate": round(dropout_rate, 2)
        }
    
    def mark_deleted(
        self,
        student_id: str,
        reason: str,
        deleted_date: Optional[str] = None
    ) -> None:
        """
        Отмечает ученика как удаленного
        
        Args:
            student_id: ID ученика
            reason: Причина удаления
            deleted_date: Дата удаления (если None, используется текущая)
        """
        data = self._load_data()
        
        if student_id not in data:
            return
        
        if deleted_date is None:
            deleted_date = datetime.now().strftime("%Y-%m-%d")
        
        data[student_id]["deleted"] = True
        data[student_id]["deleted_date"] = deleted_date
        data[student_id]["deleted_reason"] = reason
        
        self._save_data(data)
    
    def get_all_employees_statistics(
        self,
        year: Optional[int] = None,
        month: Optional[int] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Получает статистику по всем сотрудникам
        
        Args:
            year: Год (если None, используется текущий)
            month: Месяц (1-12, если None, используется текущий)
        
        Returns:
            Словарь {user_id: {"fio": ..., "total": ..., "month": ..., "role": ...}}
        """
        if year is None or month is None:
            now = datetime.now()
            year = year or now.year
            month = month or now.month
        
        data = self._load_data()
        
        employees_stats = {}
        
        for student_id, student_info in data.items():
            # Пропускаем удаленных учеников при подсчете привлеченных
            if student_info.get("deleted", False):
                continue
            
            user_id = student_info.get("added_by_user_id")
            if not user_id:
                continue
            
            if user_id not in employees_stats:
                employees_stats[user_id] = {
                    "user_id": user_id,
                    "fio": None,  # Будет заполнено из role_storage
                    "role": student_info.get("user_role", "unknown"),
                    "total": 0,
                    "month": 0
                }
            
            # Подсчитываем общее количество
            employees_stats[user_id]["total"] += 1
            
            # Подсчитываем за месяц
            date_added = student_info.get("date_added", "")
            if date_added:
                try:
                    added_date = datetime.strptime(date_added, "%Y-%m-%d")
                    if added_date.year == year and added_date.month == month:
                        employees_stats[user_id]["month"] += 1
                except ValueError:
                    pass
        
        return employees_stats
    
    def get_deleted_students_statistics(
        self,
        year: Optional[int] = None,
        month: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Получает статистику по удаленным ученикам
        
        Args:
            year: Год (если None, используется текущий)
            month: Месяц (1-12, если None, используется текущий)
        
        Returns:
            Словарь со статистикой ухода
        """
        if year is None or month is None:
            now = datetime.now()
            year = year or now.year
            month = month or now.month
        
        data = self._load_data()
        
        deleted_in_month = []
        deleted_by_city = {}
        deleted_by_group = {}
        
        total_students = len([s for s in data.values() if not s.get("deleted", False)])
        total_deleted = len([s for s in data.values() if s.get("deleted", False)])
        
        for student_id, student_info in data.items():
            if not student_info.get("deleted", False):
                continue
            
            deleted_date = student_info.get("deleted_date", "")
            if not deleted_date:
                continue
            
            try:
                deleted_date_obj = datetime.strptime(deleted_date, "%Y-%m-%d")
                if deleted_date_obj.year == year and deleted_date_obj.month == month:
                    city = student_info.get("city_name", "Не указан")
                    group = student_info.get("group_name", "Не указана")
                    
                    deleted_in_month.append({
                        "student_id": student_id,
                        "student_fio": student_info.get("student_fio", "Неизвестно"),
                        "city_name": city,
                        "group_name": group,
                        "deleted_date": deleted_date,
                        "deleted_reason": student_info.get("deleted_reason", "")
                    })
                    
                    # Подсчитываем по городам
                    if city not in deleted_by_city:
                        deleted_by_city[city] = 0
                    deleted_by_city[city] += 1
                    
                    # Подсчитываем по группам
                    group_key = f"{city} - {group}"
                    if group_key not in deleted_by_group:
                        deleted_by_group[group_key] = 0
                    deleted_by_group[group_key] += 1
            except ValueError:
                continue
        
        # Вычисляем процент ухода
        dropout_rate = 0.0
        if total_students + total_deleted > 0:
            dropout_rate = (total_deleted / (total_students + total_deleted)) * 100
        
        return {
            "deleted_in_month": len(deleted_in_month),
            "deleted_list": deleted_in_month,
            "deleted_by_city": deleted_by_city,
            "deleted_by_group": deleted_by_group,
            "total_students": total_students,
            "total_deleted": total_deleted,
            "dropout_rate": round(dropout_rate, 2)
        }
