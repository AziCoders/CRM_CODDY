"""Сервис для работы с оплатами"""
import json
import re
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timedelta
from bot.config import ROOT_DIR, CITY_MAPPING
from src.CRUD.crud_payment import NotionPaymentUpdater


class PaymentService:
    """Сервис для работы с оплатами"""
    
    def __init__(self):
        self.root_dir = ROOT_DIR
    
    def get_current_month(self, city_name: str) -> str:
        """Получает текущий месяц на русском"""
        month_order = [
            "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
            "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
        ]
        now_month_index = datetime.now().month - 1
        return month_order[now_month_index]
    
    def get_student_payment_info(self, city_name: str, student_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Получает информацию об оплате ученика
        
        Args:
            city_name: Название города (русское)
            student_data: Данные ученика из students.json
        
        Returns:
            Словарь с информацией об оплате или None
        """
        city_en = CITY_MAPPING.get(city_name, city_name)
        payments_path = self.root_dir / f"data/{city_en}/payments.json"
        
        if not payments_path.exists():
            return None
        
        try:
            with open(payments_path, "r", encoding="utf-8") as f:
                payments_data = json.load(f)
            
            student_fio = student_data.get("ФИО", "").strip().lower()
            student_id = student_data.get("ID", "")
            
            payments_list = payments_data.get("payments", [])
            
            # Ищем по ФИО или student_id
            for payment in payments_list:
                payment_fio = payment.get("ФИО", "").strip().lower()
                payment_student_id = payment.get("student_id", "")
                
                if payment_fio == student_fio or payment_student_id == student_id:
                    return payment
            
            return None
        except Exception as e:
            print(f"Ошибка загрузки информации об оплате: {e}")
            return None
    
    def get_payment_status_for_month(self, payment_data: Optional[Dict[str, Any]], month: str) -> str:
        """
        Получает статус оплаты за указанный месяц
        
        Args:
            payment_data: Данные об оплате из payments.json
            month: Название месяца (русское)
        
        Returns:
            Статус оплаты или пустая строка
        """
        if not payment_data:
            return ""
        
        payments_data = payment_data.get("payments_data", {})
        return payments_data.get(month, "").strip()
    
    def format_student_info_with_payment(self, student_data: Dict[str, Any], payment_data: Optional[Dict[str, Any]], city_name: str) -> str:
        """
        Форматирует информацию об ученике с данными об оплате
        
        Args:
            student_data: Данные ученика из students.json
            payment_data: Данные об оплате из payments.json
            city_name: Название города
        
        Returns:
            Отформатированная строка с информацией
        """
        fio = student_data.get("ФИО", "Не указано").strip()
        student_url = student_data.get("student_url", "")
        phone = student_data.get("Номер родителя", "Не указан")
        parent_name = student_data.get("Имя родителя", "Не указано")
        age = student_data.get("Возраст", "Не указан")
        date_start = student_data.get("Дата поступления", "Не указана")
        group_name = student_data.get("group_name", "Не указана")
        tarif = student_data.get("Тариф", "Не указан")
        status = student_data.get("Статус", "Не указан")
        
        # Информация об оплате
        payment_date = payment_data.get("Дата оплаты", "") if payment_data else ""
        current_month = self.get_current_month(city_name)
        payment_status = self.get_payment_status_for_month(payment_data, current_month) if payment_data else ""
        
        # Формируем строку с ФИО и ссылкой
        fio_line = f"👤 <a href='{student_url}'>{fio}</a>" if student_url else f"👤 {fio}"
        
        lines = [
            fio_line,
            "",
            f"📞 Номер родителя: {phone}",
            f"👨‍👩‍👧 Имя родителя: {parent_name}",
            f"🎂 Возраст: {age}",
            f"📅 Дата поступления: {date_start}",
            "",
            f"🏫 Группа: {group_name}",
            f"💰 Тариф: {tarif}",
            f"📊 Статус: {status}",
            f"🏙️ Город: {city_name}",
            "",
            f"📅 Дата оплаты: {payment_date if payment_date else 'Не указана'}",
            f"💳 Оплата за текущий месяц: {payment_status if payment_status else 'Не указана'}"
        ]
        
        return "\n".join(lines)
    
    async def update_payment_status(
        self,
        city_name: str,
        student_identifier: str,
        status: str,
        month: Optional[str] = None
    ) -> bool:
        """
        Обновляет статус оплаты в Notion
        
        Args:
            city_name: Название города (русское)
            student_identifier: ФИО или ID ученика
            status: Статус оплаты ("Оплатил", "Написали", "Не оплатил", "Отсрочка")
            month: Месяц (если None, используется текущий)
        
        Returns:
            True если успешно, False в случае ошибки
        """
        if month is None:
            month = self.get_current_month(city_name)
        
        try:
            # Преобразуем русское название города в английское
            city_en = CITY_MAPPING.get(city_name, city_name)
            updater = NotionPaymentUpdater(city_en)
            await updater.mark_payment(student_identifier, status, month)
            return True
        except Exception as e:
            print(f"❌ Ошибка обновления статуса оплаты: {e}")
            return False
    
    async def update_payment_comment(
        self,
        city_name: str,
        student_identifier: str,
        comment: str
    ) -> bool:
        """
        Обновляет комментарий к оплате в Notion
        
        Args:
            city_name: Название города (русское)
            student_identifier: ФИО или ID ученика
            comment: Текст комментария
        
        Returns:
            True если успешно, False в случае ошибки
        """
        try:
            # Преобразуем русское название города в английское
            city_en = CITY_MAPPING.get(city_name, city_name)
            updater = NotionPaymentUpdater(city_en)
            await updater.update_comment(student_identifier, comment)
            return True
        except Exception as e:
            print(f"❌ Ошибка обновления комментария: {e}")
            return False
    
    def get_city_students(self, city_name: str) -> List[Dict[str, Any]]:
        """
        Получает список всех учеников города
        
        Args:
            city_name: Название города (русское)
        
        Returns:
            Список учеников [{"ID": "...", "ФИО": "...", "group_name": "..."}, ...]
        """
        city_en = CITY_MAPPING.get(city_name, city_name)
        students_path = self.root_dir / f"data/{city_en}/students.json"
        
        if not students_path.exists():
            return []
        
        try:
            with open(students_path, "r", encoding="utf-8") as f:
                students_data = json.load(f)
            
            all_students = []
            for group_id, group_data in students_data.items():
                group_name = group_data.get("group_name", "")
                students_list = group_data.get("students", [])
                
                for student in students_list:
                    all_students.append({
                        "ID": student.get("ID", ""),
                        "ФИО": student.get("ФИО", "").strip(),
                        "group_name": group_name,
                        "student_url": student.get("student_url", ""),
                        "Номер родителя": student.get("Номер родителя", ""),
                        "Имя родителя": student.get("Имя родителя", ""),
                        "Возраст": student.get("Возраст", ""),
                        "Дата поступления": student.get("Дата поступления", ""),
                        "Тариф": student.get("Тариф", ""),
                        "Статус": student.get("Статус", ""),
                        "Город": student.get("Город", city_name)
                    })
            
            # Сортируем по ФИО
            all_students.sort(key=lambda x: x.get("ФИО", ""))
            
            return all_students
        except Exception as e:
            print(f"Ошибка загрузки учеников для города {city_name}: {e}")
            return []
    
    def get_student_by_id(self, city_name: str, student_id: str) -> Optional[Dict[str, Any]]:
        """
        Получает данные ученика по ID
        
        Args:
            city_name: Название города (русское)
            student_id: ID ученика
        
        Returns:
            Данные ученика или None
        """
        students = self.get_city_students(city_name)
        for student in students:
            if student.get("ID") == student_id:
                return student
        return None
    
    def get_payment_statuses_for_students(self, city_name: str, student_ids: List[str]) -> Dict[str, str]:
        """
        Получает статусы оплаты за текущий месяц для списка учеников
        
        Args:
            city_name: Название города (русское)
            student_ids: Список ID учеников
        
        Returns:
            Словарь {student_id: status}
        """
        city_en = CITY_MAPPING.get(city_name, city_name)
        payments_path = self.root_dir / f"data/{city_en}/payments.json"
        
        if not payments_path.exists():
            return {}
        
        try:
            with open(payments_path, "r", encoding="utf-8") as f:
                payments_data = json.load(f)
            
            current_month = self.get_current_month(city_name)
            statuses = {}
            payments_list = payments_data.get("payments", [])
            
            for payment in payments_list:
                student_id = payment.get("student_id", "")
                if student_id in student_ids:
                    payments_data_dict = payment.get("payments_data", {})
                    status = payments_data_dict.get(current_month, "").strip()
                    if status:
                        statuses[student_id] = status
            
            return statuses
        except Exception as e:
            print(f"Ошибка загрузки статусов оплаты: {e}")
            return {}
    
    def _parse_payment_date(self, payment_date_str: str) -> int:
        """Извлекает число из строки типа '27 числа' или '6 числа'"""
        if not payment_date_str:
            return 1  # По умолчанию 1 число
        
        # Убираем пробелы и ищем число
        match = re.search(r'(\d+)', payment_date_str)
        if match:
            return int(match.group(1))
        return 1
    
    def _calculate_student_attendance_stats(
        self,
        attendance_data: Dict[str, str],
        date_fields: List[str],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, int]:
        """Рассчитывает статистику посещаемости ученика"""
        stats = {
            "total": 0,
            "present": 0,
            "late": 0,
            "absent": 0,
            "absent_reason": 0
        }
        
        for date_key, status in attendance_data.items():
            try:
                date_str = date_key.strip()
                try:
                    date_obj = datetime.strptime(date_str, "%d.%m.%Y")
                except ValueError:
                    date_obj = datetime.strptime(date_str.strip(), "%d.%m.%Y")
                
                # Проверяем границы дат
                if start_date:
                    start_date_only = datetime(start_date.year, start_date.month, start_date.day)
                    date_obj_only = datetime(date_obj.year, date_obj.month, date_obj.day)
                    if date_obj_only < start_date_only:
                        continue
                if end_date:
                    end_date_only = datetime(end_date.year, end_date.month, end_date.day)
                    date_obj_only = datetime(date_obj.year, date_obj.month, date_obj.day)
                    if date_obj_only > end_date_only:
                        continue
                
                # Проверяем, есть ли эта дата в date_fields
                if date_fields:
                    date_found = False
                    for df in date_fields:
                        if df.strip() == date_str.strip():
                            date_found = True
                            break
                    if not date_found:
                        continue
                
                status_clean = str(status).strip()
                if not status_clean:
                    continue
                
                stats["total"] += 1
                
                if status_clean.lower() == "присутствовал":
                    stats["present"] += 1
                elif status_clean.lower() == "опоздал":
                    stats["late"] += 1
                    stats["present"] += 1  # Опоздал тоже считается присутствием
                elif status_clean.lower() == "отсутствовал по причине":
                    stats["absent_reason"] += 1
                elif status_clean.lower() == "отсутствовал":
                    stats["absent"] += 1
            except (ValueError, AttributeError):
                continue
        
        return stats
    
    def get_student_monthly_attendance(
        self,
        city_name: str,
        student_id: str,
        payment_date_str: str = ""
    ) -> Tuple[str, Dict[str, int]]:
        """
        Получает посещаемость ученика за месяц на основе даты оплаты
        
        Args:
            city_name: Название города (русское)
            student_id: ID ученика
            payment_date_str: Дата оплаты (например, "17 числа")
        
        Returns:
            Tuple[строка_периода, статистика]
        """
        city_en = CITY_MAPPING.get(city_name, city_name)
        attendance_path = self.root_dir / f"data/{city_en}/attendance.json"
        
        if not attendance_path.exists():
            return "период не определен", {"total": 0, "present": 0, "late": 0, "absent": 0, "absent_reason": 0}
        
        try:
            with open(attendance_path, "r", encoding="utf-8") as f:
                attendance_data = json.load(f)
            
            # Ищем ученика в данных посещаемости
            for group_id, group_info in attendance_data.items():
                attendance_records = group_info.get("attendance", [])
                date_fields = group_info.get("fields", [])[2:]  # Пропускаем № и ФИО
                
                for record in attendance_records:
                    if record.get("student_id") == student_id:
                        att_data = record.get("attendance", {})
                        
                        # Определяем период месяца на основе дня оплаты
                        payment_day = self._parse_payment_date(payment_date_str)
                        now = datetime.now()
                        today_day = now.day
                        
                        if today_day >= payment_day:
                            # День оплаты уже прошел - считаем текущий период оплаты
                            month_start = datetime(now.year, now.month, min(payment_day, 28))
                            if now.month == 12:
                                next_month_start = datetime(now.year + 1, 1, min(payment_day, 28))
                            else:
                                next_month_start = datetime(now.year, now.month + 1, min(payment_day, 28))
                        else:
                            # День оплаты еще не наступил - считаем предыдущий период оплаты
                            if now.month == 1:
                                month_start = datetime(now.year - 1, 12, min(payment_day, 28))
                                next_month_start = datetime(now.year, 1, min(payment_day, 28))
                            else:
                                month_start = datetime(now.year, now.month - 1, min(payment_day, 28))
                                next_month_start = datetime(now.year, now.month, min(payment_day, 28))
                        
                        # Для расчета статистики учитываем только до текущей даты
                        month_end_for_stats = min(now, next_month_start - timedelta(days=1))
                        
                        stats = self._calculate_student_attendance_stats(
                            att_data, date_fields, month_start, month_end_for_stats
                        )
                        
                        # Формируем строку периода
                        month_names = {
                            1: "января", 2: "февраля", 3: "марта", 4: "апреля",
                            5: "мая", 6: "июня", 7: "июля", 8: "августа",
                            9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
                        }
                        
                        current_month_name = month_names[month_start.month]
                        next_month_name = month_names[next_month_start.month]
                        
                        period_str = f"с {month_start.strftime('%d')} {current_month_name} до {next_month_start.strftime('%d')} {next_month_name}"
                        
                        return period_str, stats
            
            return "период не определен", {"total": 0, "present": 0, "late": 0, "absent": 0, "absent_reason": 0}
        except Exception as e:
            print(f"Ошибка расчета посещаемости: {e}")
            return "период не определен", {"total": 0, "present": 0, "late": 0, "absent": 0, "absent_reason": 0}
    
    def format_student_info_with_payment_and_attendance(
        self,
        student_data: Dict[str, Any],
        payment_data: Optional[Dict[str, Any]],
        city_name: str
    ) -> str:
        """
        Форматирует информацию об ученике с данными об оплате и посещаемости
        
        Args:
            student_data: Данные ученика из students.json
            payment_data: Данные об оплате из payments.json
            city_name: Название города
        
        Returns:
            Отформатированная строка с информацией
        """
        fio = student_data.get("ФИО", "Не указано").strip()
        student_url = student_data.get("student_url", "")
        phone = student_data.get("Номер родителя", "Не указан")
        parent_name = student_data.get("Имя родителя", "Не указано")
        age = student_data.get("Возраст", "Не указан")
        date_start = student_data.get("Дата поступления", "Не указана")
        group_name = student_data.get("group_name", "Не указана")
        tarif = student_data.get("Тариф", "Не указан")
        status = student_data.get("Статус", "Не указан")
        student_id = student_data.get("ID", "")
        
        # Информация об оплате
        payment_date = payment_data.get("Дата оплаты", "") if payment_data else ""
        current_month = self.get_current_month(city_name)
        payment_status = self.get_payment_status_for_month(payment_data, current_month) if payment_data else ""
        
        # Получаем посещаемость за месяц
        period_str, attendance_stats = self.get_student_monthly_attendance(
            city_name, student_id, payment_date
        )
        
        # Формируем строку с ФИО и ссылкой
        fio_line = f"👤 <a href='{student_url}'>{fio}</a>" if student_url else f"👤 {fio}"
        
        lines = [
            fio_line,
            "",
            f"📞 Номер родителя: {phone}",
            f"👨‍👩‍👧 Имя родителя: {parent_name}",
            f"🎂 Возраст: {age}",
            f"📅 Дата поступления: {date_start}",
            "",
            f"🏫 Группа: {group_name}",
            f"💰 Тариф: {tarif}",
            f"📊 Статус: {status}",
            f"🏙️ Город: {city_name}",
            "",
            f"📅 Дата оплаты: {payment_date if payment_date else 'Не указана'}",
            f"Посещаемость {period_str}: {attendance_stats['present']}/{attendance_stats['late']}/{attendance_stats['absent']}/{attendance_stats['absent_reason']}",
            f"💳 Оплата за текущий месяц: {payment_status if payment_status else 'Не указана'}"
        ]
        
        return "\n".join(lines)

