"""Сервис для логирования действий пользователей"""
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
from bot.config import ROOT_DIR


class ActionLogger:
    """Класс для логирования действий пользователей"""
    
    def __init__(self):
        self.logs_dir = ROOT_DIR / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.logs_file = self.logs_dir / "actions.json"
        self._ensure_logs_file()
    
    def _ensure_logs_file(self):
        """Создает файл логов если его нет"""
        if not self.logs_file.exists():
            with open(self.logs_file, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=2)
    
    def _load_logs(self) -> List[Dict[str, Any]]:
        """Загружает логи из файла"""
        try:
            if not self.logs_file.exists():
                return []
            
            with open(self.logs_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
        except Exception as e:
            print(f"⚠️ Ошибка при загрузке логов: {e}")
            return []
    
    def _save_logs(self, logs: List[Dict[str, Any]]):
        """Сохраняет логи в файл"""
        try:
            # Ограничиваем количество логов (храним последние 10000 записей)
            if len(logs) > 10000:
                logs = logs[-10000:]
            
            with open(self.logs_file, "w", encoding="utf-8") as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ Ошибка при сохранении логов: {e}")
    
    def log_action(
        self,
        user_id: int,
        user_fio: str,
        username: str,
        action_type: str,
        action_details: Dict[str, Any],
        city: Optional[str] = None,
        role: Optional[str] = None
    ):
        """
        Логирует действие пользователя
        
        Args:
            user_id: ID пользователя
            user_fio: ФИО пользователя
            username: Username пользователя
            action_type: Тип действия (add_student, mark_attendance, update_payment, etc.)
            action_details: Детали действия
            city: Город (если применимо)
            role: Роль пользователя
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "date": datetime.now().strftime("%d.%m.%Y"),
            "time": datetime.now().strftime("%H:%M:%S"),
            "user": {
                "id": user_id,
                "fio": user_fio,
                "username": username,
                "role": role
            },
            "action_type": action_type,
            "action_details": action_details,
            "city": city
        }
        
        logs = self._load_logs()
        logs.append(log_entry)
        self._save_logs(logs)
    
    def get_logs(
        self,
        user_id: Optional[int] = None,
        action_type: Optional[str] = None,
        city: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Получает логи с фильтрацией
        
        Args:
            user_id: Фильтр по ID пользователя
            action_type: Фильтр по типу действия
            city: Фильтр по городу
            limit: Максимальное количество записей
        
        Returns:
            Список логов
        """
        logs = self._load_logs()
        
        # Применяем фильтры
        filtered_logs = logs
        if user_id:
            filtered_logs = [log for log in filtered_logs if log.get("user", {}).get("id") == user_id]
        if action_type:
            filtered_logs = [log for log in filtered_logs if log.get("action_type") == action_type]
        if city:
            filtered_logs = [log for log in filtered_logs if log.get("city") == city]
        
        # Возвращаем последние записи
        return filtered_logs[-limit:]
    
    def format_log_entry(self, log: Dict[str, Any]) -> str:
        """Форматирует запись лога для красивого отображения"""
        user = log.get("user", {})
        action_type = log.get("action_type", "")
        details = log.get("action_details", {})
        city = log.get("city", "")
        
        # Иконки для типов действий
        action_icons = {
            "add_student": "➕",
            "mark_attendance": "📝",
            "update_payment": "💰",
            "add_role": "👤",
            "remove_role": "🗑️",
            "update_role": "✏️",
            "generate_report": "📊",
            "sync_data": "🔄",
            "search_student": "🔍"
        }
        
        icon = action_icons.get(action_type, "📌")
        
        lines = [
            f"{icon} <b>{self._format_action_type(action_type)}</b>",
            f"👤 <b>{user.get('fio', 'Неизвестно')}</b> (@{user.get('username', 'нет')})",
            f"🆔 ID: {user.get('id', 'N/A')}",
            f"📅 {log.get('date', '')} в {log.get('time', '')}",
        ]
        
        if city:
            lines.append(f"🏙️ Город: {city}")
        
        # Добавляем детали в зависимости от типа действия
        if action_type == "add_student":
            student_info = details.get("student", {})
            lines.extend([
                "",
                "📋 <b>Информация об ученике:</b>",
                f"   👤 ФИО: {student_info.get('ФИО', 'N/A')}",
                f"   📞 Телефон: {student_info.get('Номер родителя', 'N/A')}",
                f"   🏫 Группа: {student_info.get('group_name', 'N/A')}",
                f"   🏙️ Город: {student_info.get('Город', 'N/A')}",
                f"   📅 Дата поступления: {student_info.get('Дата поступления', 'N/A')}",
            ])
        elif action_type == "mark_attendance":
            lines.extend([
                "",
                "📋 <b>Информация о посещаемости:</b>",
                f"   🏫 Группа: {details.get('group_name', 'N/A')}",
                f"   📅 Дата: {details.get('date', 'N/A')}",
                f"   👥 Учеников отмечено: {details.get('students_count', 0)}",
            ])
        elif action_type == "update_payment":
            lines.extend([
                "",
                "📋 <b>Информация об оплате:</b>",
                f"   👤 Ученик: {details.get('student_fio', 'N/A')}",
                f"   💰 Статус: {details.get('status', 'N/A')}",
                f"   📅 Месяц: {details.get('month', 'N/A')}",
            ])
            if details.get("comment"):
                lines.append(f"   💬 Комментарий: {details.get('comment')}")
        elif action_type in ["add_role", "update_role", "remove_role"]:
            target_user = details.get("target_user", {})
            lines.extend([
                "",
                "📋 <b>Информация о пользователе:</b>",
                f"   👤 ФИО: {target_user.get('fio', 'N/A')}",
                f"   🆔 ID: {target_user.get('id', 'N/A')}",
                f"   👔 Роль: {target_user.get('role', 'N/A')}",
            ])
            if target_user.get("city"):
                lines.append(f"   🏙️ Город: {target_user.get('city')}")
        elif action_type == "generate_report":
            lines.extend([
                "",
                "📋 <b>Информация об отчете:</b>",
                f"   📊 Тип: {details.get('report_type', 'N/A')}",
                f"   🏙️ Город: {details.get('city', 'Все города')}",
            ])
        elif action_type == "sync_data":
            lines.extend([
                "",
                "📋 <b>Информация о синхронизации:</b>",
                f"   🔄 Тип: {details.get('sync_type', 'N/A')}",
                f"   🏙️ Город: {details.get('city', 'Все города')}",
            ])
        
        return "\n".join(lines)
    
    def _format_action_type(self, action_type: str) -> str:
        """Форматирует тип действия для отображения"""
        action_names = {
            "add_student": "Добавление ученика",
            "mark_attendance": "Отметка посещаемости",
            "update_payment": "Обновление оплаты",
            "add_role": "Добавление роли",
            "remove_role": "Удаление роли",
            "update_role": "Обновление роли",
            "generate_report": "Генерация отчета",
            "sync_data": "Синхронизация данных",
            "search_student": "Поиск ученика"
        }
        return action_names.get(action_type, action_type)

