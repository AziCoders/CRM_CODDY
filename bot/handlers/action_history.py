"""Обработчик истории действий"""
import json
import tempfile
from pathlib import Path
from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from bot.services.action_logger import ActionLogger
from bot.keyboards.action_history_keyboards import (
    ActionHistoryCallback,
    ActionHistoryFilterCallback,
    get_action_history_keyboard,
    get_action_history_filter_keyboard
)
from bot.keyboards.reply_keyboards import get_owner_menu

router = Router()
action_logger = ActionLogger()


@router.message(F.text == "История действий")
async def cmd_action_history(message: Message, user_role: str = None):
    """Обработчик кнопки 'История действий'"""
    if user_role != "owner":
        await message.answer("❌ История действий доступна только для владельца")
        return
    
    await message.answer(
        "📜 <b>История действий</b>\n\n"
        "Выберите действие:",
        reply_markup=get_action_history_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(ActionHistoryCallback.filter())
async def process_action_history(
    callback: CallbackQuery,
    callback_data: ActionHistoryCallback,
    user_role: str = None
):
    """Обработка действий с историей"""
    if user_role != "owner":
        await callback.answer("❌ У вас нет доступа", show_alert=True)
        return
    
    action = callback_data.action
    
    if action == "view_all":
        # Показываем все действия
        logs = action_logger.get_logs(limit=50)
        
        if not logs:
            await callback.message.edit_text(
                "📜 <b>История действий</b>\n\n"
                "История пуста.",
                parse_mode="HTML",
                reply_markup=get_action_history_keyboard()
            )
            await callback.answer()
            return
        
        # Формируем сообщение с последними действиями
        formatted_logs = []
        for log in reversed(logs[-10:]):  # Показываем последние 10
            formatted_logs.append(action_logger.format_log_entry(log))
        
        text = "📜 <b>Последние действия</b>\n\n" + "\n\n" + "─" * 30 + "\n\n".join(formatted_logs)
        
        # Разбиваем на части, если слишком длинное
        if len(text) > 4000:
            text = text[:4000] + "\n\n... (показаны последние записи)"
        
        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=get_action_history_keyboard()
        )
        await callback.answer()
        return
    
    if action == "filter":
        # Показываем меню фильтров
        await callback.message.edit_text(
            "🔍 <b>Фильтры истории</b>\n\n"
            "Выберите тип фильтра:",
            parse_mode="HTML",
            reply_markup=get_action_history_filter_keyboard()
        )
        await callback.answer()
        return
    
    if action == "download_json":
        # Скачиваем JSON файл со всей историей
        await callback.answer("⏳ Формирую файл...")
        
        try:
            # Получаем все логи (без ограничений)
            all_logs = action_logger.get_logs(limit=0)  # 0 = без ограничений
            
            if not all_logs:
                await callback.message.answer(
                    "❌ История действий пуста. Нет данных для экспорта."
                )
                await callback.answer()
                return
            
            # Создаем временный файл
            temp_dir = Path(tempfile.gettempdir())
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            json_filename = f"actions_history_{timestamp}.json"
            json_path = temp_dir / json_filename
            
            # Сохраняем все логи в JSON файл
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(all_logs, f, ensure_ascii=False, indent=2)
            
            # Отправляем файл
            document = FSInputFile(json_path, filename=json_filename)
            await callback.message.answer_document(
                document,
                caption=f"📥 <b>История действий</b>\n\n"
                       f"Всего записей: {len(all_logs)}\n"
                       f"Дата экспорта: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}",
                parse_mode="HTML"
            )
            
            # Удаляем временный файл после отправки
            try:
                json_path.unlink()
            except Exception as e:
                print(f"⚠️ Не удалось удалить временный файл: {e}")
            
            await callback.answer("✅ Файл отправлен")
        except Exception as e:
            await callback.message.answer(
                f"❌ Ошибка при формировании файла: {str(e)}"
            )
            await callback.answer("❌ Ошибка")
            print(f"Ошибка при экспорте истории: {e}")
        return
    
    if action == "back":
        await callback.message.edit_text("❌ Операция отменена")
        await callback.answer()
        return


@router.callback_query(ActionHistoryFilterCallback.filter())
async def process_action_history_filter(
    callback: CallbackQuery,
    callback_data: ActionHistoryFilterCallback,
    user_role: str = None
):
    """Обработка фильтров истории"""
    if user_role != "owner":
        await callback.answer("❌ У вас нет доступа", show_alert=True)
        return
    
    filter_type = callback_data.filter_type
    filter_value = callback_data.filter_value
    
    # Получаем логи с фильтром
    if filter_type == "action_type":
        logs = action_logger.get_logs(action_type=filter_value, limit=50)
    elif filter_type == "user_id":
        try:
            user_id = int(filter_value)
            logs = action_logger.get_logs(user_id=user_id, limit=50)
        except:
            await callback.answer("❌ Неверный ID пользователя", show_alert=True)
            return
    elif filter_type == "city":
        logs = action_logger.get_logs(city=filter_value, limit=50)
    else:
        logs = action_logger.get_logs(limit=50)
    
    if not logs:
        await callback.message.edit_text(
            f"📜 <b>История действий</b>\n\n"
            f"По выбранному фильтру ничего не найдено.",
            parse_mode="HTML",
            reply_markup=get_action_history_keyboard()
        )
        await callback.answer()
        return
    
    # Формируем сообщение
    formatted_logs = []
    for log in reversed(logs[-10:]):  # Показываем последние 10
        formatted_logs.append(action_logger.format_log_entry(log))
    
    text = f"📜 <b>История действий</b>\n\nФильтр: {filter_type} = {filter_value}\n\n" + "\n\n" + "─" * 30 + "\n\n".join(formatted_logs)
    
    if len(text) > 4000:
        text = text[:4000] + "\n\n... (показаны последние записи)"
    
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_action_history_keyboard()
    )
    await callback.answer()

