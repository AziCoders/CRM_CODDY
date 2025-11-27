"""Обработчик отчетов"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from bot.services.report_service import ReportService
from bot.services.report_payments import generate_payments_report
from bot.services.role_storage import RoleStorage
from bot.keyboards.report_keyboards import (
    ReportTypeCallback,
    ReportCityCallback,
    GroupAttendanceCallback,
    get_report_keyboard,
    get_report_city_keyboard,
    get_groups_keyboard
)
from bot.config import CITY_MAPPING
from typing import Dict

router = Router()
report_service = ReportService()
role_storage = RoleStorage()

# Временное хранилище для маппинга групп (city + idx -> group_id)
# Очищается при получении нового списка групп
_groups_cache: Dict[str, Dict[int, str]] = {}


@router.message(F.text == "Отчёты")
async def cmd_reports(message: Message, user_role: str = None):
    """Обработчик кнопки 'Отчёты'"""
    # Проверяем права доступа
    if user_role is None or user_role == "pending":
        await message.answer("❌ У вас нет доступа к этой функции")
        return
    
    # Для владельца - показываем выбор города
    if user_role == "owner":
        await message.answer(
            "📊 <b>Отчёты</b>\n\n"
            "Выберите город для просмотра отчетов:",
            reply_markup=get_report_city_keyboard(),
            parse_mode="HTML"
        )
        return
    
    # Для преподавателя - показываем отчеты только по его городу
    if user_role == "teacher":
        user_data = role_storage.get_user(message.from_user.id)
        if not user_data:
            await message.answer("❌ Не удалось определить ваш город")
            return
        
        user_city = user_data.get("city", "")
        if not user_city:
            await message.answer("❌ У вас не назначен город")
            return
        
        # Показываем меню выбора типа отчета
        await message.answer(
            f"📊 <b>Отчёты по городу: {user_city}</b>\n\n"
            f"Выберите тип отчета:",
            reply_markup=get_report_keyboard(city=user_city, is_owner=False),
            parse_mode="HTML"
        )
        return
    
    # Для других ролей
    await message.answer("❌ Отчёты доступны только для владельца и преподавателей")


@router.callback_query(ReportCityCallback.filter())
async def process_city_selection(
    callback: CallbackQuery,
    callback_data: ReportCityCallback,
    user_role: str = None
):
    """Обработка выбора города для отчетов (для владельца)"""
    if user_role != "owner":
        await callback.answer("❌ У вас нет доступа", show_alert=True)
        return
    
    selected_city = callback_data.city
    
    # Показываем меню выбора типа отчета для выбранного города
    await callback.message.edit_text(
        f"📊 <b>Отчёты по городу: {selected_city}</b>\n\n"
        f"Выберите тип отчета:",
        reply_markup=get_report_keyboard(city=selected_city, is_owner=True),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(ReportTypeCallback.filter())
async def process_report_type(
    callback: CallbackQuery,
    callback_data: ReportTypeCallback,
    user_role: str = None
):
    """Обработка выбора типа отчета"""
    if user_role not in ["teacher", "owner"]:
        await callback.answer("❌ У вас нет доступа", show_alert=True)
        return
    
    # Определяем город
    city = callback_data.city
    
    # Для преподавателя получаем город из роли, если не указан в callback
    if user_role == "teacher" and not city:
        user_data = role_storage.get_user(callback.from_user.id)
        if not user_data:
            await callback.answer("❌ Не удалось определить ваш город", show_alert=True)
            return
        
        city = user_data.get("city", "")
        if not city:
            await callback.answer("❌ У вас не назначен город", show_alert=True)
            return
    
    # Для владельца город должен быть в callback
    if user_role == "owner" and not city:
        await callback.answer("❌ Не выбран город", show_alert=True)
        return
    
    report_type = callback_data.report_type
    
    try:
        # Обработка возврата к меню отчетов
        if report_type == "back_to_menu":
            await callback.message.edit_text(
                f"📊 <b>Отчёты по городу: {city}</b>\n\n"
                f"Выберите тип отчета:",
                parse_mode="HTML",
                reply_markup=get_report_keyboard(city=city, is_owner=(user_role == "owner"))
            )
            await callback.answer()
            return
        
        # Форматируем в зависимости от типа
        if report_type == "payments":
            # Новый отчет по оплатам
            try:
                summary_text, excel_path = generate_payments_report(city)
                
                # Отправляем текстовый отчет
                await callback.message.edit_text(
                    summary_text,
                    reply_markup=get_report_keyboard(city=city, is_owner=(user_role == "owner"))
                )
                
                # Отправляем Excel файл
                document = FSInputFile(excel_path)
                await callback.message.answer_document(
                    document,
                    caption=f"📊 Отчет по оплатам: {city}"
                )
                
                await callback.answer("✅ Отчет сгенерирован")
            except Exception as e:
                await callback.answer(f"❌ Ошибка при генерации отчета: {str(e)}", show_alert=True)
                print(f"Ошибка генерации отчета по оплатам: {e}")
        else:
            # Остальные отчеты
            report = report_service.get_city_report(city)
            
            if report_type == "summary":
                formatted = report_service.format_city_summary(report)
                await callback.message.edit_text(
                    formatted,
                    parse_mode="HTML",
                    reply_markup=get_report_keyboard(city=city, is_owner=(user_role == "owner"))
                )
            elif report_type == "groups_attendance":
                # Новый формат отчета по посещаемости с кнопками групп
                formatted, groups_list, idx_to_group_id = report_service.format_groups_attendance(report)
                
                # Сохраняем mapping в кэш (ключ: city_short + user_id, значение: {idx_to_group_id, full_city})
                city_short = city[:8]  # Используем первые 8 символов для callback
                cache_key = f"{city_short}_{callback.from_user.id}"
                _groups_cache[cache_key] = {
                    "idx_to_group_id": idx_to_group_id,
                    "full_city": city
                }
                
                await callback.message.edit_text(
                    formatted,
                    parse_mode="HTML",
                    reply_markup=get_groups_keyboard(city_short, groups_list)
                )
            else:
                formatted = "❌ Неизвестный тип отчета"
                await callback.message.edit_text(
                    formatted,
                    parse_mode="HTML",
                    reply_markup=get_report_keyboard(city=city, is_owner=(user_role == "owner"))
                )
            await callback.answer()
    
    except Exception as e:
        await callback.answer(f"❌ Ошибка при генерации отчета: {str(e)}", show_alert=True)
        print(f"Ошибка генерации отчета: {e}")


@router.callback_query(GroupAttendanceCallback.filter())
async def process_group_attendance(
    callback: CallbackQuery,
    callback_data: GroupAttendanceCallback,
    user_role: str = None
):
    """Обработка выбора группы для детального отчета по посещаемости"""
    if user_role not in ["teacher", "owner"]:
        await callback.answer("❌ У вас нет доступа", show_alert=True)
        return
    
    # Восстанавливаем данные из кэша
    cache_key = f"{callback_data.city}_{callback.from_user.id}"
    cache_data = _groups_cache.get(cache_key)
    
    if not cache_data:
        await callback.answer("❌ Сессия истекла. Пожалуйста, выберите отчет заново.", show_alert=True)
        return
    
    idx_to_group_id = cache_data.get("idx_to_group_id", {})
    city = cache_data.get("full_city", callback_data.city)
    
    # Получаем group_id по индексу
    group_id = idx_to_group_id.get(str(callback_data.idx))
    
    if not group_id:
        await callback.answer("❌ Группа не найдена", show_alert=True)
        return
    
    try:
        formatted, report_city = report_service.get_group_detailed_attendance(city, group_id)
        
        # Кнопка возврата к списку групп (используем сокращенное название для callback)
        from bot.keyboards.report_keyboards import ReportTypeCallback
        city_short = city[:8] if len(city) > 8 else city
        keyboard = [[InlineKeyboardButton(
            text="🔙 Назад к группам",
            callback_data=ReportTypeCallback(report_type="groups_attendance", city=city_short).pack()
        )]]
        
        await callback.message.edit_text(
            formatted,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await callback.answer()
    
    except Exception as e:
        await callback.answer(f"❌ Ошибка при загрузке отчета: {str(e)}", show_alert=True)
        print(f"Ошибка детального отчета по группе: {e}")

