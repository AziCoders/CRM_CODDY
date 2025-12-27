"""Утилиты для асинхронной работы с файлами"""
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional


async def read_json_file_async(file_path: Path) -> Dict[str, Any]:
    """
    Асинхронно читает JSON файл без блокировки event loop
    
    Args:
        file_path: Путь к файлу
        
    Returns:
        Словарь с данными из JSON, или пустой словарь если файл не существует или ошибка
    """
    if not file_path.exists():
        return {}
    
    def _read_file():
        """Синхронная функция чтения файла"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"⚠️ Ошибка декодирования JSON в {file_path}")
            return {}
        except Exception as e:
            print(f"⚠️ Ошибка чтения файла {file_path}: {e}")
            return {}
    
    # Выполняем чтение в отдельном потоке
    try:
        return await asyncio.to_thread(_read_file)
    except Exception as e:
        print(f"⚠️ Ошибка при асинхронном чтении {file_path}: {e}")
        return {}


async def write_json_file_async(file_path: Path, data: Dict[str, Any], indent: int = 2) -> bool:
    """
    Асинхронно записывает данные в JSON файл без блокировки event loop
    
    Args:
        file_path: Путь к файлу
        data: Данные для записи
        indent: Отступ для форматирования JSON
        
    Returns:
        True если запись успешна, False в случае ошибки
    """
    def _write_file():
        """Синхронная функция записи файла"""
        try:
            # Создаем директорию если не существует
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Записываем во временный файл, потом переименовываем (атомарная запись)
            temp_path = file_path.with_suffix(file_path.suffix + '.tmp')
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=indent)
            
            # Атомарная замена
            temp_path.replace(file_path)
            return True
        except Exception as e:
            print(f"⚠️ Ошибка записи файла {file_path}: {e}")
            # Удаляем временный файл если был создан
            try:
                temp_path = file_path.with_suffix(file_path.suffix + '.tmp')
                if temp_path.exists():
                    temp_path.unlink()
            except:
                pass
            return False
    
    # Выполняем запись в отдельном потоке
    try:
        return await asyncio.to_thread(_write_file)
    except Exception as e:
        print(f"⚠️ Ошибка при асинхронной записи {file_path}: {e}")
        return False

