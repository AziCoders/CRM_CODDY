"""Обработчик информации о городе, группах и учениках"""
import json
from pathlib import Path
from typing import Dict, Any, List
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from bot.keyboards.info_keyboards import (
    InfoMenuCallback,
    CityInfoCallback,
    InfoActionCallback,
    GroupInfoCallback,
    GroupStudentsCallback,
    StudentSelectCallback,
    BackCallback,
    get_info_cities_keyboard,
    get_info_menu_keyboard,
    get_groups_list_keyboard,
    get_group_info_keyboard,
    get_students_list_keyboard,
    get_back_to_info_keyboard
)
from bot.keyboards.student_profile_keyboards import get_student_profile_keyboard
from bot.services.group_service import GroupService
from bot.services.role_storage import RoleStorage
from bot.services.student_search import StudentSearchService
from bot.config import CITIES, CITY_MAPPING, ROOT_DIR

router = Router()
group_service = GroupService()
role_storage = RoleStorage()
search_service = StudentSearchService()


def convert_city_en_to_ru(city_en: str) -> str:
    """Преобразует английское название города (возможно сокращенное) обратно в русское"""
    if not city_en:
        return ""
    
    # Сначала пробуем точное совпадение
    for ru_name, en_name in CITY_MAPPING.items():
        if en_name == city_en:
            return ru_name
    
    # Если не нашли, пробуем по началу (так как city_en может быть обрезан до 6 символов)
    for ru_name, en_name in CITY_MAPPING.items():
        # Проверяем, начинается ли полное название с сокращенного
        if en_name.startswith(city_en) or (len(city_en) >= 3 and city_en.lower() in en_name.lower()):
            return ru_name
    
    # Если все еще не нашли, пробуем обратное преобразование
    reverse_mapping = {v: k for k, v in CITY_MAPPING.items()}
    for en_full, ru_full in reverse_mapping.items():
        if en_full.startswith(city_en) or (len(city_en) >= 3 and city_en.lower() in en_full.lower()):
            return ru_full
    
    # Последний fallback - пробуем найти в CITIES по частичному совпадению
    for city in CITIES:
        city_en_from_mapping = CITY_MAPPING.get(city, "")
        if city_en_from_mapping and (city_en in city_en_from_mapping or city_en_from_mapping.startswith(city_en)):
            return city
    
    # Если ничего не нашли, возвращаем как есть (может быть это уже русское название)
    return city_en


def load_city_info(city_name: str) -> Dict[str, str]:
    """Загружает информацию о городе из main_page_info.json"""
    city_en = CITY_MAPPING.get(city_name, city_name)
    info_path = ROOT_DIR / f"data/{city_en}/main_page_info.json"
    
    if not info_path.exists():
        return {}
    
    try:
        with open(info_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Ошибка загрузки main_page_info.json для {city_name}: {e}")
        return {}


def format_city_info(info: Dict[str, str]) -> str:
    """Форматирует информацию о городе"""
    lines = []
    if info.get("address"):
        lines.append(info["address"])
    if info.get("office_hours"):
        lines.append(info["office_hours"])
    if info.get("teacher"):
        lines.append(info["teacher"])
    if info.get("contact"):
        lines.append(info["contact"])
    if info.get("number_seats"):
        lines.append(info["number_seats"])
    
    return "\n".join(lines) if lines else "❌ Информация не найдена"


def get_groups_statistics(city_name: str) -> Dict[str, Any]:
    """Получает статистику по группам города"""
    groups = group_service.get_city_groups(city_name)
    
    if not groups:
        return {
            "total_groups": 0,
            "total_students": 0,
            "avg_students": 0,
            "groups": []
        }
    
    total_students = sum(group.get("total_students", 0) for group in groups)
    avg_students = total_students / len(groups) if groups else 0
    
    return {
        "total_groups": len(groups),
        "total_students": total_students,
        "avg_students": round(avg_students, 1),
        "groups": groups
    }


def format_groups_statistics(stats: Dict[str, Any]) -> str:
    """Форматирует статистику по группам"""
    lines = [
        f"📊 <b>Статистика по группам</b>\n",
        f"🏫 Всего групп: {stats['total_groups']}",
        f"👥 Всего учеников: {stats['total_students']}",
        f"📈 Среднее в группе: {stats['avg_students']}",
    ]
    return "\n".join(lines)


def get_group_info(city_name: str, group_id: str) -> Dict[str, Any]:
    """Получает информацию о группе"""
    groups = group_service.get_city_groups(city_name)
    
    for group in groups:
        if group.get("group_id") == group_id:
            return group
    
    return {}


def format_group_info(group: Dict[str, Any], city_name: str) -> str:
    """Форматирует информацию о группе"""
    lines = [
        f"🏫 <b>{group.get('group_name', 'Без названия')}</b>\n",
        f"🏙️ Город: {city_name}",
        f"👥 Учеников: {group.get('total_students', 0)}",
    ]
    
    if group.get("status"):
        lines.append(f"📊 Статус: {group.get('status')}")
    
    return "\n".join(lines)


def get_group_students(city_name: str, group_id: str) -> List[Dict[str, Any]]:
    """Получает список учеников группы"""
    students_data = search_service._load_city_students(city_name)
    
    if not students_data:
        print(f"⚠️ Не удалось загрузить данные учеников для города {city_name}")
        return []
    
    if group_id not in students_data:
        print(f"⚠️ Группа {group_id} не найдена в данных для города {city_name}")
        return []
    
    group_data = students_data[group_id]
    students = group_data.get("students", [])
    
    if not students:
        print(f"⚠️ В группе {group_id} нет учеников")
        return []
    
    # Добавляем group_id и group_name к каждому ученику
    for student in students:
        student["group_id"] = group_id
        student["group_name"] = group_data.get("group_name", "")
        # Убеждаемся, что у ученика есть ID
        if not student.get("ID"):
            print(f"⚠️ Ученик {student.get('ФИО', 'N/A')} не имеет ID")
    
    return students


@router.message(F.text == "Информация")
async def cmd_info(message: Message, user_role: str = None, user_city: str = None):
    """Обработчик кнопки 'Информация'"""
    if user_role is None or user_role == "pending":
        await message.answer("❌ У вас нет доступа к этой функции")
        return
    
    # Для преподавателя показываем только свой город
    if user_role == "teacher":
        if not user_city:
            await message.answer("❌ Не указан ваш город")
            return
        
        # Показываем меню информации для города преподавателя
        await message.answer(
            f"📋 <b>Информация</b>\n\n"
            f"🏙️ Город: {user_city}",
            parse_mode="HTML",
            reply_markup=get_info_menu_keyboard(user_city)
        )
        return
    
    # Для менеджера и владельца показываем выбор города
    await message.answer(
        "🏙️ Выберите город:",
        reply_markup=get_info_cities_keyboard(CITIES)
    )


@router.callback_query(CityInfoCallback.filter())
async def handle_city_info(
    callback: CallbackQuery,
    callback_data: CityInfoCallback,
    user_role: str = None
):
    """Обработка выбора города в информации"""
    city_name = callback_data.city
    
    # Проверяем права для преподавателя
    if user_role == "teacher":
        user_data = role_storage.get_user(callback.from_user.id)
        if user_data:
            user_city = user_data.get("city", "")
            if user_city != city_name:
                await callback.answer("❌ У вас нет доступа к этому городу", show_alert=True)
                return
    
    await callback.message.edit_text(
        f"📋 <b>Информация</b>\n\n"
        f"🏙️ Город: {city_name}",
        parse_mode="HTML",
        reply_markup=get_info_menu_keyboard(city_name)
    )
    await callback.answer()


@router.callback_query(InfoActionCallback.filter())
async def handle_info_action(
    callback: CallbackQuery,
    callback_data: InfoActionCallback,
    user_role: str = None
):
    """Обработка действий в информации (информация о городе или группы)"""
    action = callback_data.action
    city_en = callback_data.city_en or ""
    
    # Преобразуем английское название обратно в русское
    city_name = convert_city_en_to_ru(city_en)
    
    # Проверяем права для преподавателя
    if user_role == "teacher":
        user_data = role_storage.get_user(callback.from_user.id)
        if user_data:
            user_city = user_data.get("city", "")
            if user_city != city_name:
                await callback.answer("❌ У вас нет доступа к этому городу", show_alert=True)
                return
    
    if action == "info":
        # Показываем информацию о городе
        info = load_city_info(city_name)
        formatted = format_city_info(info)
        
        await callback.message.edit_text(
            formatted,
            parse_mode="HTML",
            reply_markup=get_back_to_info_keyboard(city_name)
        )
    elif action == "groups":
        # Показываем статистику по группам и список групп
        stats = get_groups_statistics(city_name)
        stats_text = format_groups_statistics(stats)
        
        await callback.message.edit_text(
            stats_text,
            parse_mode="HTML",
            reply_markup=get_groups_list_keyboard(stats["groups"], city_name)
        )
    
    await callback.answer()


@router.callback_query(GroupInfoCallback.filter())
async def handle_group_info(
    callback: CallbackQuery,
    callback_data: GroupInfoCallback,
    user_role: str = None
):
    """Обработка выбора группы"""
    group_id_short = callback_data.group_id or ""
    city_en = callback_data.city_en or ""
    
    # Преобразуем английское название обратно в русское
    city_name = convert_city_en_to_ru(city_en)
    
    # Проверяем права для преподавателя
    if user_role == "teacher":
        user_data = role_storage.get_user(callback.from_user.id)
        if user_data:
            user_city = user_data.get("city", "")
            if user_city != city_name:
                await callback.answer("❌ У вас нет доступа к этому городу", show_alert=True)
                return
    
    # Ищем группу по сокращенному ID
    groups = group_service.get_city_groups(city_name)
    group = None
    group_id_full = None
    
    # Нормализуем group_id_short - берем первые 16 символов (как в клавиатуре)
    group_id_short_normalized = group_id_short[:16] if len(group_id_short) > 16 else group_id_short
    
    for g in groups:
        group_id_from_data = g.get("group_id", "")
        group_id_no_dashes = group_id_from_data.replace("-", "")
        group_id_short_from_data = group_id_no_dashes[:16]  # Берем первые 16 символов (как в клавиатуре)
        # Используем точное сравнение первых 16 символов
        if group_id_short_from_data == group_id_short_normalized:
            group = g
            group_id_full = group_id_from_data
            break
    
    if not group:
        await callback.answer("❌ Группа не найдена", show_alert=True)
        return
    
    formatted = format_group_info(group, city_name)
    
    await callback.message.edit_text(
        formatted,
        parse_mode="HTML",
        reply_markup=get_group_info_keyboard(group_id_full, city_name)
    )
    await callback.answer()


@router.callback_query(GroupStudentsCallback.filter())
async def handle_group_students(
    callback: CallbackQuery,
    callback_data: GroupStudentsCallback,
    user_role: str = None
):
    """Обработка просмотра учеников группы"""
    group_id_short = callback_data.group_id or ""
    city_en = callback_data.city_en or ""
    
    # Преобразуем английское название обратно в русское
    city_name = convert_city_en_to_ru(city_en)
    
    # Проверяем права для преподавателя
    if user_role == "teacher":
        user_data = role_storage.get_user(callback.from_user.id)
        if user_data:
            user_city = user_data.get("city", "")
            if user_city != city_name:
                await callback.answer("❌ У вас нет доступа к этому городу", show_alert=True)
                return
    
    # Ищем группу по сокращенному ID
    groups = group_service.get_city_groups(city_name)
    group_id_full = None
    group_name = "Без названия"
    
    # Нормализуем group_id_short - берем первые 16 символов (как в клавиатуре)
    group_id_short_normalized = group_id_short[:16] if len(group_id_short) > 16 else group_id_short
    
    for g in groups:
        group_id_from_data = g.get("group_id", "")
        group_id_no_dashes = group_id_from_data.replace("-", "")
        group_id_short_from_data = group_id_no_dashes[:16]  # Берем первые 16 символов (как в клавиатуре)
        # Используем точное сравнение первых 16 символов
        if group_id_short_from_data == group_id_short_normalized:
            group_id_full = group_id_from_data
            group_name = g.get("group_name", "Без названия")
            break
    
    if not group_id_full:
        await callback.answer("❌ Группа не найдена", show_alert=True)
        return
    
    students = get_group_students(city_name, group_id_full)
    
    if not students:
        await callback.message.edit_text(
            "❌ В группе нет учеников",
            reply_markup=get_back_to_info_keyboard(city_name)
        )
        await callback.answer()
        return
    
    students_text = f"👥 <b>Ученики группы: {group_name}</b>\n\n"
    students_text += f"Всего учеников: {len(students)}\n\n"
    students_text += "Выберите ученика:"
    
    await callback.message.edit_text(
        students_text,
        parse_mode="HTML",
        reply_markup=get_students_list_keyboard(students, group_id_full, city_name)
    )
    await callback.answer()


@router.callback_query(StudentSelectCallback.filter())
async def handle_student_select(
    callback: CallbackQuery,
    callback_data: StudentSelectCallback,
    user_role: str = None
):
    """Обработка выбора ученика из группы"""
    student_id_short = callback_data.student_id or ""
    city_en = callback_data.city_en or ""
    group_id_short = callback_data.group_id or ""
    
    # Преобразуем английское название обратно в русское
    city_name = convert_city_en_to_ru(city_en)
    
    # Проверяем права для преподавателя
    if user_role == "teacher":
        user_data = role_storage.get_user(callback.from_user.id)
        if user_data:
            user_city = user_data.get("city", "")
            if user_city != city_name:
                await callback.answer("❌ У вас нет доступа к этому городу", show_alert=True)
                return
    
    # Ищем группу по сокращенному ID
    groups = group_service.get_city_groups(city_name)
    group_id_full = None
    
    print(f"🔍 Восстановление группы: group_id_short={group_id_short} (len={len(group_id_short)}), city={city_name}")
    
    # Нормализуем group_id_short - берем первые 10 символов (для StudentSelectCallback используется 10)
    group_id_short_normalized = group_id_short[:10] if len(group_id_short) > 10 else group_id_short
    print(f"   Нормализованный group_id_short: {group_id_short_normalized}")
    
    for g in groups:
        group_id_from_data = g.get("group_id", "")
        group_id_no_dashes = group_id_from_data.replace("-", "")
        group_id_short_from_data = group_id_no_dashes[:10]  # Берем первые 10 символов для сравнения (StudentSelectCallback использует 10)
        print(f"   Проверяю: {g.get('group_name', 'N/A')} -> ID={group_id_from_data[:30]}... -> short={group_id_short_from_data}")
        # Используем точное сравнение первых 10 символов
        if group_id_short_from_data == group_id_short_normalized:
            group_id_full = group_id_from_data
            print(f"✅ Найдена группа: {g.get('group_name', 'N/A')}, ID={group_id_full}")
            break
    
    if not group_id_full:
        print(f"❌ Группа не найдена для group_id_short={group_id_short} (normalized={group_id_short_normalized})")
        print(f"   Доступные группы:")
        for g in groups[:3]:
            gid = g.get("group_id", "")
            gid_short = gid.replace("-", "")[:10] if gid else ""
            print(f"     - {g.get('group_name', 'N/A')}: {gid_short}")
        await callback.answer("❌ Группа не найдена", show_alert=True)
        return
    
    # Получаем данные ученика
    students = get_group_students(city_name, group_id_full)
    
    if not students:
        await callback.answer("❌ В группе нет учеников", show_alert=True)
        return
    
    student_data = None
    student_id_full = None
    
    # Отладочная информация
    print(f"🔍 Поиск ученика: student_id_short={student_id_short}, group_id_full={group_id_full}, students_count={len(students)}")
    
    if not student_id_short:
        print(f"❌ student_id_short пустой!")
        await callback.answer("❌ Ошибка: ID ученика не указан", show_alert=True)
        return
    
    for student in students:
        student_id_from_data = student.get("ID", "")
        if not student_id_from_data:
            print(f"⚠️ Ученик {student.get('ФИО', 'N/A')} не имеет ID")
            continue
        
        student_id_no_dashes = student_id_from_data.replace("-", "")
        # Проверяем, начинается ли полный ID (без дефисов) с сокращенного
        if student_id_no_dashes.startswith(student_id_short):
            student_data = student.copy()
            student_id_full = student_id_from_data
            print(f"✅ Найден ученик: {student_data.get('ФИО', 'N/A')}, ID={student_id_full}")
            break
    
    if not student_data:
        # Дополнительная отладка
        print(f"❌ Ученик не найден. Ищем: '{student_id_short}'")
        print(f"   Проверяемые ID (первые 5):")
        for i, student in enumerate(students[:5]):  # Показываем первые 5 для отладки
            sid = student.get("ID", "")
            sid_no_dashes = sid.replace("-", "") if sid else ""
            sid_short = sid_no_dashes[:16] if sid_no_dashes else ""
            matches = sid_no_dashes.startswith(student_id_short) if sid_no_dashes and student_id_short else False
            print(f"   {i+1}. {student.get('ФИО', 'N/A')[:30]}:")
            print(f"      ID={sid}")
            print(f"      short={sid_short}")
            print(f"      matches={matches}")
        await callback.answer("❌ Ученик не найден", show_alert=True)
        return
    
    # Форматируем и показываем профиль
    from bot.handlers.student_search import format_full_info
    formatted = format_full_info(student_data)
    # Показываем кнопку "Назад", так как профиль получен через кнопки
    keyboard = get_student_profile_keyboard(student_id_full, city_name, group_id_full, show_back=True, user_role=user_role)
    
    if keyboard:
        await callback.message.edit_text(
            formatted,
            parse_mode="HTML",
            reply_markup=keyboard
        )
    else:
        await callback.message.edit_text(
            formatted,
            parse_mode="HTML"
        )
    await callback.answer()


@router.callback_query(BackCallback.filter())
async def handle_back(
    callback: CallbackQuery,
    callback_data: BackCallback,
    user_role: str = None
):
    """Обработка кнопки Назад"""
    try:
        level = callback_data.level
        city_en = callback_data.city_en or ""
        group_id_short = callback_data.group_id or ""
        
        # Отладочная информация
        print(f"🔙 Обработка кнопки Назад: level={level}, city_en={city_en}, group_id_short={group_id_short}")
        
        # Преобразуем английское название обратно в русское (если нужно)
        city_name = convert_city_en_to_ru(city_en) if city_en else None
        
        print(f"🔙 Преобразование: city_en={city_en} -> city_name={city_name}")
        
        if level == "main":
            # Возврат к выбору города (для менеджера/владельца) или главному меню
            if user_role in ["manager", "owner"]:
                await callback.message.edit_text(
                    "🏙️ Выберите город:",
                    reply_markup=get_info_cities_keyboard(CITIES)
                )
            else:
                # Для преподавателя возврат к меню информации города
                user_data = role_storage.get_user(callback.from_user.id)
                if user_data:
                    user_city = user_data.get("city", "")
                    await callback.message.edit_text(
                        f"📋 <b>Информация</b>\n\n"
                        f"🏙️ Город: {user_city}",
                        parse_mode="HTML",
                        reply_markup=get_info_menu_keyboard(user_city)
                    )
        elif level == "city":
            # Возврат к меню информации города
            if city_name:
                await callback.message.edit_text(
                    f"📋 <b>Информация</b>\n\n"
                    f"🏙️ Город: {city_name}",
                    parse_mode="HTML",
                    reply_markup=get_info_menu_keyboard(city_name)
                )
            else:
                print(f"❌ Ошибка: city_name не найден для level=city, city_en={city_en}")
                await callback.answer("❌ Ошибка: не удалось определить город", show_alert=True)
        elif level == "groups":
            # Возврат к списку групп
            if city_name:
                stats = get_groups_statistics(city_name)
                stats_text = format_groups_statistics(stats)
                await callback.message.edit_text(
                    stats_text,
                    parse_mode="HTML",
                    reply_markup=get_groups_list_keyboard(stats["groups"], city_name)
                )
            else:
                print(f"❌ Ошибка: city_name не найден для level=groups, city_en={city_en}")
                await callback.answer("❌ Ошибка: не удалось определить город", show_alert=True)
        elif level == "group":
            # Возврат к информации о группе
            if city_name and group_id_short:
                # Ищем группу по сокращенному ID (используется 10 символов из get_students_list_keyboard)
                groups = group_service.get_city_groups(city_name)
                group = None
                group_id_full = None
                
                # Нормализуем group_id_short - берем первые 10 символов
                group_id_short_normalized = group_id_short[:10] if len(group_id_short) > 10 else group_id_short
                
                for g in groups:
                    group_id_from_data = g.get("group_id", "")
                    group_id_no_dashes = group_id_from_data.replace("-", "")
                    group_id_short_from_data = group_id_no_dashes[:10]  # Берем первые 10 символов
                    # Используем точное сравнение первых 10 символов
                    if group_id_short_from_data == group_id_short_normalized:
                        group = g
                        group_id_full = group_id_from_data
                        break
                
                if group:
                    formatted = format_group_info(group, city_name)
                    await callback.message.edit_text(
                        formatted,
                        parse_mode="HTML",
                        reply_markup=get_group_info_keyboard(group_id_full, city_name)
                    )
                else:
                    print(f"❌ Ошибка: группа не найдена для group_id_short={group_id_short}")
                    await callback.answer("❌ Ошибка: группа не найдена", show_alert=True)
            else:
                print(f"❌ Ошибка: недостаточно данных для level=group, city_name={city_name}, group_id_short={group_id_short}")
                await callback.answer("❌ Ошибка: недостаточно данных", show_alert=True)
        
        await callback.answer()
    except Exception as e:
        print(f"❌ Ошибка в handle_back: {e}", exc_info=True)
        await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data == "certificates_not_implemented")
async def handle_certificates_not_implemented(callback: CallbackQuery):
    """Обработка кнопки формирования сертификатов (пока не реализовано)"""
    await callback.answer("⏳ Функция формирования сертификатов будет добавлена позже", show_alert=True)
