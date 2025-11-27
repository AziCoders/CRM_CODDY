"""Обработчик отчетов"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from bot.services.report_service import ReportService
from bot.services.role_storage import RoleStorage
from bot.keyboards.report_keyboards import (
    ReportTypeCallback,
    ReportCityCallback,
    PaymentsPaginationCallback,
    get_report_keyboard,
    get_report_city_keyboard,
    get_payments_pagination_keyboard
)
from bot.config import CITY_MAPPING

router = Router()
report_service = ReportService()
role_storage = RoleStorage()


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
            # Отчет по оплатам с пагинацией
            report = report_service.get_payments_report(city)
            formatted, has_prev, has_next = report_service.format_payments_report(report, page=0)
            
            await callback.message.edit_text(
                formatted,
                parse_mode="HTML",
                reply_markup=get_payments_pagination_keyboard(city, 0, has_prev, has_next)
            )
            await callback.answer()
        else:
            # Остальные отчеты
            report = report_service.get_city_report(city)
            
            if report_type == "summary":
                formatted = report_service.format_city_summary(report)
            elif report_type == "city_attendance":
                formatted = report_service.format_city_attendance(report)
            elif report_type == "groups_attendance":
                formatted = report_service.format_groups_attendance(report)
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


@router.callback_query(PaymentsPaginationCallback.filter())
async def process_payments_pagination(
    callback: CallbackQuery,
    callback_data: PaymentsPaginationCallback,
    user_role: str = None
):
    """Обработка пагинации отчета по оплатам"""
    if user_role not in ["teacher", "owner"]:
        await callback.answer("❌ У вас нет доступа", show_alert=True)
        return
    
    city = callback_data.city
    page = callback_data.page
    
    if page < 0:
        await callback.answer("❌ Это первая страница", show_alert=True)
        return
    
    try:
        report = report_service.get_payments_report(city)
        formatted, has_prev, has_next = report_service.format_payments_report(report, page=page)
        
        await callback.message.edit_text(
            formatted,
            parse_mode="HTML",
            reply_markup=get_payments_pagination_keyboard(city, page, has_prev, has_next)
        )
        await callback.answer()
    
    except Exception as e:
        await callback.answer(f"❌ Ошибка при загрузке страницы: {str(e)}", show_alert=True)
        print(f"Ошибка пагинации отчета: {e}")

