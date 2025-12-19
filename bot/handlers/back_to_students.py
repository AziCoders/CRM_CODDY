"""Обработчик кнопки Назад к списку учеников группы"""
from aiogram import Router
from aiogram.types import CallbackQuery
from bot.keyboards.student_profile_keyboards import BackToStudentsCallback
from bot.keyboards.info_keyboards import get_students_list_keyboard
from bot.services.group_service import GroupService
from bot.services.role_storage import RoleStorage
from bot.services.student_search import StudentSearchService
from bot.config import CITY_MAPPING

router = Router()
group_service = GroupService()
role_storage = RoleStorage()
search_service = StudentSearchService()


def get_group_students(city_name: str, group_id: str):
    """Получает список учеников группы"""
    students_data = search_service._load_city_students(city_name)
    
    if group_id not in students_data:
        return []
    
    group_data = students_data[group_id]
    students = group_data.get("students", [])
    
    # Добавляем group_id и group_name к каждому ученику
    for student in students:
        student["group_id"] = group_id
        student["group_name"] = group_data.get("group_name", "")
    
    return students


@router.callback_query(BackToStudentsCallback.filter())
async def handle_back_to_students(
    callback: CallbackQuery,
    callback_data: BackToStudentsCallback,
    user_role: str = None
):
    """Обработка кнопки Назад к списку учеников группы"""
    group_id_short = callback_data.group_id
    city_en = callback_data.city_en
    
    # Преобразуем английское название обратно в русское
    city_name = None
    for ru_name, en_name in CITY_MAPPING.items():
        if en_name == city_en or en_name.startswith(city_en):
            city_name = ru_name
            break
    
    if not city_name:
        city_name = city_en  # Fallback
    
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
    
    # Нормализуем group_id_short - берем первые 10 символов
    group_id_short_normalized = group_id_short[:10] if len(group_id_short) > 10 else group_id_short
    
    for g in groups:
        group_id_from_data = g.get("group_id", "")
        group_id_no_dashes = group_id_from_data.replace("-", "")
        group_id_short_from_data = group_id_no_dashes[:10]  # Берем первые 10 символов
        # Используем точное сравнение первых 10 символов
        if group_id_short_from_data == group_id_short_normalized:
            group_id_full = group_id_from_data
            group_name = g.get("group_name", "Без названия")
            break
    
    if not group_id_full:
        await callback.answer("❌ Группа не найдена", show_alert=True)
        return
    
    # Получаем список учеников
    students = get_group_students(city_name, group_id_full)
    
    if not students:
        await callback.message.edit_text(
            "❌ В группе нет учеников",
            reply_markup=None
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
