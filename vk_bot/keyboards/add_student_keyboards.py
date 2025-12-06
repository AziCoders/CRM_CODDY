"""Клавиатуры для добавления ученика (VK)"""
from vkbottle import Keyboard, KeyboardButtonColor, Text, Callback
from bot.config import CITIES

def get_cities_keyboard():
    """Клавиатура выбора города"""
    keyboard = Keyboard(one_time=True, inline=True)
    
    for i, city in enumerate(CITIES):
        if i > 0 and i % 2 == 0:
            keyboard.row()
        keyboard.add(Callback(city, payload={"cmd": "select_city", "city": city}))
    
    keyboard.row()
    keyboard.add(Callback("Отмена", payload={"cmd": "cancel"}), color=KeyboardButtonColor.NEGATIVE)
    
    return keyboard.get_json()

def get_groups_keyboard(groups: list):
    """Клавиатура выбора группы"""
    keyboard = Keyboard(one_time=True, inline=True)
    
    for i, group in enumerate(groups):
        group_name = group.get("group_name", "Без названия")
        group_id = group.get("group_id")
        
        # Обрезаем название, если слишком длинное (ограничение VK)
        if len(group_name) > 40:
            group_name = group_name[:37] + "..."
            
        keyboard.add(Callback(group_name, payload={"cmd": "select_group", "group_id": group_id}))
        keyboard.row()
        
    keyboard.add(Callback("Отмена", payload={"cmd": "cancel"}), color=KeyboardButtonColor.NEGATIVE)
    
    return keyboard.get_json()

def get_cancel_keyboard():
    """Клавиатура отмены"""
    keyboard = Keyboard(one_time=True, inline=True)
    keyboard.add(Callback("Отмена", payload={"cmd": "cancel"}), color=KeyboardButtonColor.NEGATIVE)
    return keyboard.get_json()
