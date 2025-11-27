"""Сервис для генерации отчетов"""
import json
from pathlib import Path
from typing import Dict, Any, List
from statistics import mean
from bot.config import ROOT_DIR, CITY_MAPPING


class ReportService:
    """Сервис для генерации отчетов по городу"""
    
    def __init__(self):
        self.root_dir = ROOT_DIR
    
    def _load_json(self, path: Path) -> Dict[str, Any]:
        """Безопасная загрузка JSON"""
        if not path.exists():
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Ошибка загрузки {path}: {e}")
            return {}
    
    def get_city_report(self, city_name: str) -> Dict[str, Any]:
        """Генерирует полный отчет по городу"""
        city_en = CITY_MAPPING.get(city_name, city_name)
        base = self.root_dir / f"data/{city_en}"
        
        groups = self._load_json(base / "groups.json")
        students = self._load_json(base / "students.json")
        attendance = self._load_json(base / "attendance.json")
        payments = self._load_json(base / "payments.json")
        main_info = self._load_json(base / "main_page_info.json")
        
        report = {
            "city": city_name,
            "info": main_info,
            "groups_count": len(groups),
            "total_students": 0,
            "groups": [],
            "avg_attendance_percent_city": 0,
        }
        
        attendance_percents = []
        
        # Проход по группам
        for group_id, group_data in groups.items():
            group_name = group_data.get("Название группы", "Без названия")
            group_students_block = students.get(group_id, {})
            group_attendance_block = attendance.get(group_id, {})
            
            # Список учеников
            student_list = group_students_block.get("students", [])
            total_group_students = group_students_block.get("total_students", 0)
            report["total_students"] += total_group_students
            
            # Посещаемость
            attendance_records = group_attendance_block.get("attendance", [])
            attendance_fields = group_attendance_block.get("fields", [])
            # Пропускаем первые 2 поля (№, ФИО), остальное - даты
            date_fields = attendance_fields[2:] if len(attendance_fields) > 2 else []
            total_lessons = len(date_fields)
            
            attendance_percent = 0
            if total_lessons > 0 and total_group_students > 0:
                visited = 0
                total_possible = total_lessons * total_group_students
                
                for rec in attendance_records:
                    attendance_data = rec.get("attendance", {})
                    # Считаем присутствия (разные варианты статусов)
                    for date_field in date_fields:
                        status = str(attendance_data.get(date_field, "")).strip()
                        # Считаем как присутствие: "Присутствовал", "Был", "Опоздал"
                        # Приводим к нижнему регистру для сравнения
                        status_lower = status.lower()
                        if status_lower in ["присутствовал", "был", "опоздал"]:
                            visited += 1
                
                if total_possible > 0:
                    attendance_percent = round((visited / total_possible) * 100, 2)
            
            attendance_percents.append(attendance_percent)
            
            # Добавляем группу в отчет
            report["groups"].append({
                "group_id": group_id,
                "group_name": group_name,
                "total_students": total_group_students,
                "attendance_percent": attendance_percent,
                "total_lessons": total_lessons,
                "attendance_records": len(attendance_records),
            })
        
        # Итоги по городу
        if attendance_percents:
            report["avg_attendance_percent_city"] = round(mean(attendance_percents), 2)
        
        return report
    
    def format_city_summary(self, report: Dict[str, Any]) -> str:
        """Форматирует краткую сводку по городу"""
        lines = [
            f"📊 <b>Отчет по городу: {report['city']}</b>",
            "",
            f"🏫 Групп: {report['groups_count']}",
            f"👥 Всего учеников: {report['total_students']}",
        ]
        
        if report.get('avg_attendance_percent_city', 0) > 0:
            lines.append(f"📈 Средняя посещаемость: {report['avg_attendance_percent_city']}%")
        
        return "\n".join(lines)
    
    def format_city_attendance(self, report: Dict[str, Any]) -> str:
        """Форматирует отчет о посещаемости по городу"""
        lines = [
            f"📈 <b>Посещаемость по городу: {report['city']}</b>",
            "",
            f"📊 Средняя посещаемость: {report.get('avg_attendance_percent_city', 0)}%",
            "",
            "<b>По группам:</b>",
        ]
        
        for group in report.get("groups", []):
            group_name = group.get("group_name", "Без названия")
            attendance = group.get("attendance_percent", 0)
            students = group.get("total_students", 0)
            lessons = group.get("total_lessons", 0)
            
            lines.append(
                f"🏫 {group_name}\n"
                f"   👥 Учеников: {students}\n"
                f"   📅 Уроков: {lessons}\n"
                f"   📈 Посещаемость: {attendance}%"
            )
            lines.append("")
        
        return "\n".join(lines)
    
    def format_groups_attendance(self, report: Dict[str, Any]) -> str:
        """Форматирует детальный отчет о посещаемости по группам"""
        lines = [
            f"📋 <b>Детальный отчет по группам: {report['city']}</b>",
            "",
        ]
        
        for group in report.get("groups", []):
            group_name = group.get("group_name", "Без названия")
            attendance = group.get("attendance_percent", 0)
            students = group.get("total_students", 0)
            lessons = group.get("total_lessons", 0)
            records = group.get("attendance_records", 0)
            
            lines.append(f"🏫 <b>{group_name}</b>")
            lines.append(f"   👥 Учеников: {students}")
            lines.append(f"   📅 Проведено уроков: {lessons}")
            lines.append(f"   📝 Записей посещаемости: {records}")
            lines.append(f"   📈 Посещаемость: {attendance}%")
            lines.append("")
        
        return "\n".join(lines)
    
    def _find_student_group(self, students_data: Dict[str, Any], structure_data: Dict[str, Any] = None, student_id: str = None, fio: str = None) -> Dict[str, str]:
        """Находит группу ученика по student_id или ФИО. Возвращает dict с group_name, group_id, group_url"""
        result = {
            "group_name": "Неизвестно",
            "group_id": "",
            "group_url": ""
        }
        
        if not students_data:
            return result
        
        # Сначала пытаемся найти по student_id
        if student_id:
            for group_id, group_data in students_data.items():
                group_name = group_data.get("group_name", "")
                for student in group_data.get("students", []):
                    if student.get("ID") == student_id:
                        result["group_name"] = group_name
                        result["group_id"] = group_id
                        # Формируем URL группы в Notion
                        result["group_url"] = f"https://www.notion.so/{group_id.replace('-', '')}"
                        return result
        
        # Если не нашли по ID, ищем по ФИО
        if fio:
            fio_lower = fio.strip().lower()
            for group_id, group_data in students_data.items():
                group_name = group_data.get("group_name", "")
                for student in group_data.get("students", []):
                    student_fio = student.get("ФИО", "").strip().lower()
                    if student_fio == fio_lower:
                        result["group_name"] = group_name
                        result["group_id"] = group_id
                        # Формируем URL группы в Notion
                        result["group_url"] = f"https://www.notion.so/{group_id.replace('-', '')}"
                        return result
        
        return result
    
    def get_payments_report(self, city_name: str) -> Dict[str, Any]:
        """Генерирует отчет по оплатам для города"""
        city_en = CITY_MAPPING.get(city_name, city_name)
        base = self.root_dir / f"data/{city_en}"
        
        payments_data = self._load_json(base / "payments.json")
        students = self._load_json(base / "students.json")
        structure = self._load_json(base / "structure.json")
        
        payments_list = payments_data.get("payments", [])
        fields = payments_data.get("fields", [])
        
        # Получаем месяцы из полей (исключаем служебные поля)
        month_fields = [f for f in fields if f not in ["Дата оплаты", "ФИО", "Phone", "Комментарий"]]
        
        report = {
            "city": city_name,
            "total_students": len(payments_list),
            "month_fields": month_fields,
            "payments": [],
            "statistics": {}
        }
        
        # Статистика по месяцам
        for month in month_fields:
            report["statistics"][month] = {
                "paid": 0,
                "not_paid": 0,
                "written": 0,
                "empty": 0
            }
        
        # Обрабатываем каждую оплату
        for payment in payments_list:
            payments_data_dict = payment.get("payments_data", {})
            fio = payment.get("ФИО", "Неизвестно")
            phone = payment.get("Phone", "")
            comment = payment.get("Комментарий", "")
            payment_date = payment.get("Дата оплаты", "")
            student_id = payment.get("student_id", "")
            student_url = payment.get("student_url", "")
            
            # Находим группу ученика
            group_info = self._find_student_group(students, structure, student_id, fio)
            
            payment_info = {
                "fio": fio,
                "phone": phone,
                "comment": comment,
                "payment_date": payment_date,
                "student_url": student_url,
                "group_name": group_info["group_name"],
                "group_url": group_info["group_url"],
                "months": {}
            }
            
            # Собираем информацию по каждому месяцу
            for month in month_fields:
                # Получаем статус из payments_data, если это словарь
                if isinstance(payments_data_dict, dict):
                    status = payments_data_dict.get(month, "")
                else:
                    # Если payments_data не словарь, пытаемся получить напрямую из payment
                    status = payment.get(month, "")
                
                # Обрабатываем статус
                if isinstance(status, str):
                    status = status.strip()
                else:
                    status = str(status).strip() if status else ""
                
                payment_info["months"][month] = status
                
                # Обновляем статистику
                status_lower = status.lower()
                if status_lower == "оплатил":
                    report["statistics"][month]["paid"] += 1
                elif status_lower == "не оплатил":
                    report["statistics"][month]["not_paid"] += 1
                elif status_lower == "написали":
                    report["statistics"][month]["written"] += 1
                else:
                    report["statistics"][month]["empty"] += 1
            
            report["payments"].append(payment_info)
        
        return report
    
    def format_payments_report_txt(self, report: Dict[str, Any]) -> Path:
        """Форматирует отчет по оплатам в .txt файл"""
        import tempfile
        from datetime import datetime
        
        # Создаем временный файл
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        city_en = CITY_MAPPING.get(report['city'], report['city'])
        filename = f"payments_report_{city_en}_{timestamp}.txt"
        
        temp_file = self.root_dir / "temp" / filename
        temp_file.parent.mkdir(parents=True, exist_ok=True)
        
        month_fields = report.get("month_fields", [])
        payments = report.get("payments", [])
        
        with open(temp_file, "w", encoding="utf-8") as f:
            # Заголовок
            f.write(f"ОТЧЕТ ПО ОПЛАТАМ: {report['city']}\n")
            f.write(f"Дата формирования: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n")
            f.write(f"Всего учеников: {report['total_students']}\n")
            f.write("=" * 80 + "\n\n")
            
            # Записываем каждую строку: ФИО, ГРУППА, затем остальная информация
            for payment in payments:
                fio = payment.get("fio", "Неизвестно")
                group_name = payment.get("group_name", "Неизвестно")
                phone = payment.get("phone", "")
                comment = payment.get("comment", "")
                payment_date = payment.get("payment_date", "")
                months = payment.get("months", {})
                
                # Основная строка: ФИО, ГРУППА
                line_parts = [fio, group_name]
                
                # Добавляем телефон, если есть
                if phone:
                    line_parts.append(f"Телефон: {phone}")
                
                # Добавляем дату оплаты, если есть
                if payment_date:
                    line_parts.append(f"Дата оплаты: {payment_date}")
                
                # Статусы по месяцам
                for month in month_fields:
                    status = months.get(month, "")
                    if status:
                        line_parts.append(f"{month}: {status}")
                
                # Комментарий
                if comment:
                    line_parts.append(f"Комментарий: {comment}")
                
                # Записываем всю информацию в одну строку
                f.write(" | ".join(line_parts) + "\n")
        
        return temp_file
    
    def format_payments_report(self, report: Dict[str, Any], page: int = 0, per_page: int = 10) -> tuple[str, bool, bool]:
        """
        Форматирует отчет по оплатам для отображения в сообщении с пагинацией.
        Возвращает: (текст, есть_предыдущая_страница, есть_следующая_страница)
        """
        payments = report.get("payments", [])
        month_fields = report.get("month_fields", [])
        total = len(payments)
        
        # Вычисляем пагинацию
        start_idx = page * per_page
        end_idx = min(start_idx + per_page, total)
        page_payments = payments[start_idx:end_idx]
        
        # Формируем текст
        lines = [
            f"💰 <b>Отчет по оплатам: {report['city']}</b>",
            f"👥 Всего учеников: {total}",
            f"📄 Страница {page + 1} из {(total + per_page - 1) // per_page}",
            ""
        ]
        
        # Добавляем информацию по каждому ученику на текущей странице
        for payment in page_payments:
            fio = payment.get("fio", "Неизвестно")
            student_url = payment.get("student_url", "")
            group_name = payment.get("group_name", "Неизвестно")
            group_url = payment.get("group_url", "")
            months = payment.get("months", {})
            
            # Формируем строку с ФИО (ссылка) и группой (ссылка)
            if student_url:
                fio_text = f'<a href="{student_url}">{fio}</a>'
            else:
                fio_text = fio
            
            if group_url:
                group_text = f'<a href="{group_url}">{group_name}</a>'
            else:
                group_text = group_name
            
            lines.append(f"👤 {fio_text}/{group_text}")
            
            # Статусы по месяцам
            statuses = []
            for month in month_fields:
                status = months.get(month, "")
                if status:
                    statuses.append(f"{month}: {status}")
            
            if statuses:
                lines.append(f"\n   {' | '.join(statuses)}")
            
            lines.append("")
        
        has_prev = page > 0
        has_next = end_idx < total
        
        return "\n".join(lines), has_prev, has_next

