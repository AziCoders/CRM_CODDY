"""Обработчик свободных мест для SMM"""
from aiogram import Router, F
from aiogram.types import Message
from bot.services.group_service import GroupService
from bot.services.smm_tracking_service import SMMTrackingService
from bot.services.role_storage import RoleStorage
from bot.config import CITIES

router = Router()
group_service = GroupService()
smm_tracking = SMMTrackingService()
role_storage = RoleStorage()


@router.message(F.text == "Свободные места")
async def cmd_free_places(message: Message, user_role: str = None):
    """Обработчик кнопки 'Свободные места'"""
    # Проверяем права доступа
    if user_role not in ["owner", "manager", "smm"]:
        await message.answer("❌ Свободные места доступны только для владельца, менеджера и SMM")
        return
    
    # Для SMM показываем упрощенный отчет
    if user_role == "smm":
        await show_smm_free_places(message)
        return
    
    await message.answer("⏳ Загружаю информацию о свободных местах...")
    
    # Собираем информацию по всем городам
    all_cities_info = []
    
    for city_name in CITIES:
        try:
            # Получаем количество мест в классе
            total_seats = await group_service.get_city_seats(city_name)
            
            if total_seats == 0:
                continue  # Пропускаем города без информации о местах
            
            # Получаем группы города
            groups = await group_service.get_city_groups(city_name)
            
            if not groups:
                continue  # Пропускаем города без групп
            
            city_info = {
                "city": city_name,
                "total_seats": total_seats,
                "groups": []
            }
            
            # Обрабатываем каждую группу
            for group in groups:
                group_name = group.get("group_name", "Без названия")
                total_students = group.get("total_students", 0)
                free_places = total_seats - total_students
                
                city_info["groups"].append({
                    "name": group_name,
                    "total_students": total_students,
                    "free_places": free_places,
                    "status": group.get("status", "")
                })
            
            if city_info["groups"]:
                all_cities_info.append(city_info)
        except Exception as e:
            print(f"Ошибка обработки города {city_name}: {e}")
            continue
    
    if not all_cities_info:
        await message.answer("❌ Не удалось загрузить информацию о свободных местах")
        return
    
    # Формируем сообщение
    lines = ["📊 <b>Свободные места по группам</b>\n"]
    
    for city_info in all_cities_info:
        city_name = city_info["city"]
        total_seats = city_info["total_seats"]
        groups = city_info["groups"]
        
        # Подсчитываем общее количество свободных мест в городе
        total_free = sum(g.get("free_places", 0) for g in groups)
        total_occupied = sum(g.get("total_students", 0) for g in groups)
        
        lines.append(f"\n🏙️ <b>{city_name}</b>")
        lines.append(f"   📦 Всего мест: {total_seats}")
        lines.append(f"   👥 Занято: {total_occupied}")
        lines.append(f"   ✅ Свободно: {total_free}")
        lines.append("")
        
        # Показываем группы с свободными местами
        groups_with_free = [g for g in groups if g.get("free_places", 0) > 0]
        groups_full = [g for g in groups if g.get("free_places", 0) <= 0]
        
        if groups_with_free:
            lines.append("   <b>Группы со свободными местами:</b>")
            for group in groups_with_free:
                group_name = group["name"]
                free = group["free_places"]
                occupied = group["total_students"]
                status_icon = "🟢" if free > 0 else "🔴"
                lines.append(f"   {status_icon} {group_name}: {occupied}/{total_seats} (свободно: {free})")
        
        if groups_full:
            lines.append("")
            lines.append("   <b>Группы без свободных мест:</b>")
            for group in groups_full:
                group_name = group["name"]
                occupied = group["total_students"]
                lines.append(f"   🔴 {group_name}: {occupied}/{total_seats} (заполнена)")
        
        lines.append("")
    
    # Итоговая статистика
    total_cities = len(all_cities_info)
    total_all_seats = sum(c["total_seats"] for c in all_cities_info)
    total_all_occupied = sum(sum(g.get("total_students", 0) for g in c["groups"]) for c in all_cities_info)
    total_all_free = total_all_seats - total_all_occupied
    
    lines.append("─" * 30)
    lines.append(f"\n📈 <b>Итого по всем городам:</b>")
    lines.append(f"   🏙️ Городов: {total_cities}")
    lines.append(f"   📦 Всего мест: {total_all_seats}")
    lines.append(f"   👥 Занято: {total_all_occupied}")
    lines.append(f"   ✅ Свободно: {total_all_free}")
    
    message_text = "\n".join(lines)
    
    # Разбиваем на части, если сообщение слишком длинное
    if len(message_text) > 4000:
        # Разбиваем по городам
        current_message = ["📊 <b>Свободные места по группам</b>\n"]
        for city_info in all_cities_info:
            city_name = city_info["city"]
            total_seats = city_info["total_seats"]
            groups = city_info["groups"]
            
            total_free = sum(g.get("free_places", 0) for g in groups)
            total_occupied = sum(g.get("total_students", 0) for g in groups)
            
            city_lines = [
                f"\n🏙️ <b>{city_name}</b>",
                f"   📦 Всего мест: {total_seats}",
                f"   👥 Занято: {total_occupied}",
                f"   ✅ Свободно: {total_free}",
                ""
            ]
            
            groups_with_free = [g for g in groups if g.get("free_places", 0) > 0]
            groups_full = [g for g in groups if g.get("free_places", 0) <= 0]
            
            if groups_with_free:
                city_lines.append("   <b>Группы со свободными местами:</b>")
                for group in groups_with_free:
                    group_name = group["name"]
                    free = group["free_places"]
                    occupied = group["total_students"]
                    city_lines.append(f"   🟢 {group_name}: {occupied}/{total_seats} (свободно: {free})")
            
            if groups_full:
                city_lines.append("")
                city_lines.append("   <b>Группы без свободных мест:</b>")
                for group in groups_full:
                    group_name = group["name"]
                    occupied = group["total_students"]
                    city_lines.append(f"   🔴 {group_name}: {occupied}/{total_seats} (заполнена)")
            
            city_text = "\n".join(city_lines)
            
            # Если добавление этого города превысит лимит, отправляем текущее сообщение
            if len("\n".join(current_message) + city_text) > 4000:
                await message.answer("\n".join(current_message), parse_mode="HTML")
                current_message = [city_text]
            else:
                current_message.append(city_text)
        
        # Отправляем последнее сообщение
        if current_message:
            await message.answer("\n".join(current_message), parse_mode="HTML")
        
        # Отправляем итоговую статистику
        summary_lines = [
            "─" * 30,
            f"\n📈 <b>Итого по всем городам:</b>",
            f"   🏙️ Городов: {total_cities}",
            f"   📦 Всего мест: {total_all_seats}",
            f"   👥 Занято: {total_all_occupied}",
            f"   ✅ Свободно: {total_all_free}"
        ]
        await message.answer("\n".join(summary_lines), parse_mode="HTML")
    else:
        await message.answer(message_text, parse_mode="HTML")


async def show_smm_free_places(message: Message):
    """Показывает упрощенный отчет о свободных местах для SMM"""
    await message.answer("⏳ Загружаю информацию о свободных местах...")
    
    # Собираем информацию по городам (свободные места в каждом городе и группах)
    cities_info = {}  # {city_name: {"total_free": int, "groups": [{"name": str, "free": int}]}}
    total_free_places = 0
    
    for city_name in CITIES:
        try:
            total_seats = await group_service.get_city_seats(city_name)
            if total_seats == 0:
                continue
            
            groups = await group_service.get_city_groups(city_name)
            if not groups:
                continue
            
            # Собираем информацию о группах со свободными местами
            city_groups = []
            city_free_places = 0
            
            for group in groups:
                group_name = group.get("group_name", "Без названия")
                total_students = group.get("total_students", 0)
                free_places = total_seats - total_students
                
                if free_places > 0:
                    city_groups.append({
                        "name": group_name,
                        "free": free_places
                    })
                    city_free_places += free_places
            
            if city_free_places > 0:
                cities_info[city_name] = {
                    "total_free": city_free_places,
                    "groups": city_groups
                }
                total_free_places += city_free_places
        except Exception as e:
            print(f"Ошибка обработки города {city_name}: {e}")
            continue
    
    # Формируем сообщение в нужном формате
    lines = []
    
    # Общее количество свободных мест
    lines.append(f"Всего свободных мест: {total_free_places}")
    lines.append("")
    
    # Список городов с количеством свободных мест и группами
    for city_name in sorted(cities_info.keys()):
        city_data = cities_info[city_name]
        free_count = city_data["total_free"]
        groups_list = city_data["groups"]
        
        lines.append(f"{city_name}:")
        lines.append(f"Свободных мест: {free_count}")
        
        # Добавляем информацию о группах
        for group_info in groups_list:
            lines.append(f"  - {group_info['name']}: {group_info['free']} мест")
        
        lines.append("")
    
    message_text = "\n".join(lines)
    await message.answer(message_text, parse_mode="HTML")

