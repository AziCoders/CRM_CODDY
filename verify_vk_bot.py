"""Скрипт для проверки импортов и синтаксиса VK бота"""
import sys
import os
from pathlib import Path

# Добавляем корневую директорию в путь
ROOT_DIR = Path(__file__).resolve().parent
sys.path.append(str(ROOT_DIR))

def verify_imports():
    print("[INFO] Checking imports...")
    try:
        from vk_bot.config import VK_BOT_TOKEN
        print("[OK] Config imported")
        
        from vk_bot.handlers import start, owner_role_assign, student_search, add_student
        print("[OK] Handlers imported")
        
        from vk_bot.services.role_storage import RoleStorage
        print("[OK] RoleStorage imported")
        
        print("[SUCCESS] All modules imported successfully!")
        return True
    except ImportError as e:
        print(f"[ERROR] Import error: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        return False

if __name__ == "__main__":
    if verify_imports():
        print("\n[READY] Bot is ready to start! Don't forget to add VK_BOT_TOKEN to .env")
        print("Run: python -m vk_bot.main")
    else:
        sys.exit(1)
