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
from bot.services.id_mapping import id_mapping_service
from bot.config import CITIES, CITY_MAPPING, ROOT_DIR

router = Router()
group_service = GroupService()
role_storage = RoleStorage()
search_service = StudentSearchService()

# Обратный маппинг для O(1) преобразования английского названия в русское
CITY_EN_TO_RU = {en: ru for ru, en in CITY_MAPPING.items()}


def convert_city_en_to_ru(city_en: str) -> str:
    """Преобразует английское название города в русское (O(1) lookup)"""
    if not city_en:
        return ""
    return CITY_EN_TO_RU.get(city_en, "")


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
    
    if not city_name:
        await callback.answer("❌ Ошибка: не удалось определить город", show_alert=True)
        return
    
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
    group_id = callback_data.group_id or ""
    city_en = callback_data.city_en or ""
    
    if not group_id:
        await callback.answer("❌ Ошибка: ID группы не указан", show_alert=True)
        return
    
    # Преобразуем английское название обратно в русское
    city_name = convert_city_en_to_ru(city_en)
    
    if not city_name:
        await callback.answer("❌ Ошибка: не удалось определить город", show_alert=True)
        return
    
    # Проверяем права для преподавателя
    if user_role == "teacher":
        user_data = role_storage.get_user(callback.from_user.id)
        if user_data:
            user_city = user_data.get("city", "")
            if user_city != city_name:
                await callback.answer("❌ У вас нет доступа к этому городу", show_alert=True)
                return
    
    # Ищем группу по полному ID
    groups = group_service.get_city_groups(city_name)
    group = None
    
    for g in groups:
        if g.get("group_id") == group_id:
            group = g
            break
    
    if not group:
        await callback.answer("❌ Группа не найдена", show_alert=True)
        return
    
    formatted = format_group_info(group, city_name)
    
    await callback.message.edit_text(
        formatted,
        parse_mode="HTML",
        reply_markup=get_group_info_keyboard(group_id, city_name)
    )
    await callback.answer()


@router.callback_query(GroupStudentsCallback.filter())
async def handle_group_students(
    callback: CallbackQuery,
    callback_data: GroupStudentsCallback,
    user_role: str = None
):
    """Обработка просмотра учеников группы"""
    group_id = callback_data.group_id or ""
    city_en = callback_data.city_en or ""
    
    if not group_id:
        await callback.answer("❌ Ошибка: ID группы не указан", show_alert=True)
        return
    
    # Преобразуем английское название обратно в русское
    city_name = convert_city_en_to_ru(city_en)
    
    if not city_name:
        await callback.answer("❌ Ошибка: не удалось определить город", show_alert=True)
        return
    
    # Проверяем права для преподавателя
    if user_role == "teacher":
        user_data = role_storage.get_user(callback.from_user.id)
        if user_data:
            user_city = user_data.get("city", "")
            if user_city != city_name:
                await callback.answer("❌ У вас нет доступа к этому городу", show_alert=True)
                return
    
    # Проверяем существование группы
    groups = group_service.get_city_groups(city_name)
    group = None
    group_name = "Без названия"
    
    for g in groups:
        if g.get("group_id") == group_id:
            group = g
            group_name = g.get("group_name", "Без названия")
            break
    
    if not group:
        await callback.answer("❌ Группа не найдена", show_alert=True)
        return
    
    students = get_group_students(city_name, group_id)
    
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
        reply_markup=get_students_list_keyboard(students, group_id, city_name)
    )
    await callback.answer()


@router.callback_query(StudentSelectCallback.filter())
async def handle_student_select(
    callback: CallbackQuery,
    callback_data: StudentSelectCallback,
    user_role: str = None
):
    """Обработка выбора ученика из группы"""
    student_id_short = (callback_data.student_id or "").strip()
    city_en_short = (callback_data.city_en or "").strip()
    group_id_short = (callback_data.group_id or "").strip()
    
    if not student_id_short:
        await callback.answer("❌ Ошибка: ID ученика не указан", show_alert=True)
        return
    
    if not group_id_short:
        await callback.answer("❌ Ошибка: ID группы не указан", show_alert=True)
        return
    
    if not city_en_short:
        await callback.answer("❌ Ошибка: город не указан", show_alert=True)
        return
    
    # Преобразуем сокращенное английское название обратно в полное и русское
    city_name = None
    city_en_full = None
    for ru_name, en_name in CITY_MAPPING.items():
        if en_name.startswith(city_en_short):
            city_name = ru_name
            city_en_full = en_name
            break
    
    if not city_name:
        await callback.answer("❌ Ошибка: не удалось определить город", show_alert=True)
        return
    
    # Проверяем права для преподавателя
    if user_role == "teacher":
        user_data = role_storage.get_user(callback.from_user.id)
        if user_data:
            user_city = user_data.get("city", "")
            if user_city != city_name:
                await callback.answer("❌ У вас нет доступа к этому городу", show_alert=True)
                return
    
    # Получаем полные ID из маппинга
    group_id_full = id_mapping_service.get_full_id("group", group_id_short)
    student_id_full = id_mapping_service.get_full_id("student", student_id_short)
    
    if not group_id_full:
        await callback.answer("❌ Группа не найдена. Попробуйте выбрать группу заново", show_alert=True)
        return
    
    if not student_id_full:
        await callback.answer("❌ Ученик не найден. Попробуйте выбрать ученика заново", show_alert=True)
        return
    
    # Получаем данные ученика
    students = get_group_students(city_name, group_id_full)
    
    if not students:
        await callback.answer("❌ В группе нет учеников", show_alert=True)
        return
    
    # Ищем ученика по полному ID
    student_data = None
    for student in students:
        if student.get("ID") == student_id_full:
            student_data = student.copy()
            break
    
    if not student_data:
        await callback.answer("❌ Ученик не найден в группе", show_alert=True)
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
    # Обязательный ответ в начале для предотвращения "залипания" кнопки
    await callback.answer()
    
    try:
        level = callback_data.level
        city_en = callback_data.city_en or ""
        group_id = callback_data.group_id or ""
        
        # Валидация уровня
        if level not in ["main", "city", "groups", "group", "students"]:
            await callback.answer("❌ Ошибка: неверный уровень навигации", show_alert=True)
            return
        
        # Преобразуем английское название обратно в русское (если нужно)
        city_name = convert_city_en_to_ru(city_en) if city_en else None
        
        # Валидация контекста для уровней, требующих город
        if level in ["city", "groups", "group", "students"]:
            if not city_en:
                await callback.answer("❌ Ошибка: не указан город", show_alert=True)
                return
            if not city_name:
                await callback.answer("❌ Ошибка: не удалось определить город", show_alert=True)
                return
        
        # Валидация контекста для уровней, требующих группу
        if level in ["group", "students"]:
            if not group_id:
                await callback.answer("❌ Ошибка: не указана группа", show_alert=True)
                return
        
        # Обработка каждого уровня навигации
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
                    if user_city:
                        await callback.message.edit_text(
                            f"📋 <b>Информация</b>\n\n"
                            f"🏙️ Город: {user_city}",
                            parse_mode="HTML",
                            reply_markup=get_info_menu_keyboard(user_city)
                        )
                    else:
                        await callback.answer("❌ Ошибка: не указан ваш город", show_alert=True)
                else:
                    await callback.answer("❌ Ошибка: не удалось получить данные пользователя", show_alert=True)
        
        elif level == "city":
            # Возврат к меню информации города
            await callback.message.edit_text(
                f"📋 <b>Информация</b>\n\n"
                f"🏙️ Город: {city_name}",
                parse_mode="HTML",
                reply_markup=get_info_menu_keyboard(city_name)
            )
        
        elif level == "groups":
            # Возврат к списку групп
            stats = get_groups_statistics(city_name)
            stats_text = format_groups_statistics(stats)
            await callback.message.edit_text(
                stats_text,
                parse_mode="HTML",
                reply_markup=get_groups_list_keyboard(stats["groups"], city_name)
            )
        
        elif level == "group":
            # Возврат к информации о группе
            groups = group_service.get_city_groups(city_name)
            group = None
            
            # Ищем группу по полному ID
            for g in groups:
                if g.get("group_id") == group_id:
                    group = g
                    break
            
            if not group:
                await callback.answer("❌ Ошибка: группа не найдена", show_alert=True)
                return
            
            formatted = format_group_info(group, city_name)
            await callback.message.edit_text(
                formatted,
                parse_mode="HTML",
                reply_markup=get_group_info_keyboard(group_id, city_name)
            )
        
        elif level == "students":
            # Возврат к списку учеников группы
            groups = group_service.get_city_groups(city_name)
            group = None
            group_name = "Без названия"
            
            # Проверяем существование группы
            for g in groups:
                if g.get("group_id") == group_id:
                    group = g
                    group_name = g.get("group_name", "Без названия")
                    break
            
            if not group:
                await callback.answer("❌ Ошибка: группа не найдена", show_alert=True)
                return
            
            students = get_group_students(city_name, group_id)
            
            if not students:
                await callback.message.edit_text(
                    "❌ В группе нет учеников",
                    reply_markup=get_back_to_info_keyboard(city_name)
                )
                return
            
            students_text = f"👥 <b>Ученики группы: {group_name}</b>\n\n"
            students_text += f"Всего учеников: {len(students)}\n\n"
            students_text += "Выберите ученика:"
            
            await callback.message.edit_text(
                students_text,
                parse_mode="HTML",
                reply_markup=get_students_list_keyboard(students, group_id, city_name)
            )
    
    except Exception as e:
        print(f"❌ Ошибка в handle_back: {e}", exc_info=True)
        await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data == "certificates_not_implemented")
async def handle_certificates_not_implemented(callback: CallbackQuery):
    """Обработка кнопки формирования сертификатов (пока не реализовано)"""
    await callback.answer("⏳ Функция формирования сертификатов будет добавлена позже", show_alert=True)
