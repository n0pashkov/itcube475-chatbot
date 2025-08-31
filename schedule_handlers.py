"""
Обработчики для управления расписанием
"""
import asyncio
import aiosqlite
import os
import tempfile
from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, CallbackQuery, Document
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

from database import db
from chat_handler import ChatType, ChatBehavior, require_permission
from enhanced_keyboards import get_schedule_settings_keyboard
from schedule_parser import schedule_parser

schedule_router = Router()

# Состояния для загрузки файлов
class ScheduleStates(StatesGroup):
    waiting_for_xlsx_file = State()

@schedule_router.callback_query(F.data == "schedule_upload_xlsx")
async def schedule_upload_xlsx_callback(callback: CallbackQuery, state: FSMContext):
    """Загрузка XLSX файла с расписанием"""
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав для выполнения этой команды.", show_alert=True)
        return
    
    text = (
        "📤 *Загрузка XLSX файла с расписанием*\n\n"
        "Отправьте файл Excel (.xlsx) с расписанием.\n\n"
        "Файл должен содержать следующие колонки:\n"
        "• Направление\n"
        "• Преподаватель\n"
        "• Понедельник, Вторник, Среда, Четверг, Пятница, Суббота\n"
        "• Кабинет\n\n"
        "⚠️ Внимание: загрузка нового файла заменит текущее расписание!"
    )
    
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="❌ Отменить загрузку", callback_data="cancel_xlsx_upload"))
    builder.add(InlineKeyboardButton(text="⬅️ Назад к настройкам расписания", callback_data="settings_schedule"))
    
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=builder.as_markup()
    )
    
    # Устанавливаем состояние ожидания файла
    await state.set_state(ScheduleStates.waiting_for_xlsx_file)
    await callback.answer()

@schedule_router.callback_query(F.data == "cancel_xlsx_upload")
async def cancel_xlsx_upload_callback(callback: CallbackQuery, state: FSMContext):
    """Отмена загрузки XLSX файла"""
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав для выполнения этой команды.", show_alert=True)
        return
    
    await state.clear()
    
    text = (
        "📅 *Настройки расписания*\n\n"
        "Здесь вы можете управлять расписанием IT-Cube:\n\n"
        "• 📤 Загрузить новый XLSX файл с расписанием\n"
        "• 📊 Просмотреть статистику текущего расписания\n"
        "• 🔄 Обновить данные из CSV файла\n\n"
        "Выберите действие:"
    )
    
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_schedule_settings_keyboard()
    )
    await callback.answer()

@schedule_router.message(ScheduleStates.waiting_for_xlsx_file, F.document)
async def handle_xlsx_file(message: Message, state: FSMContext):
    """Обработка загруженного XLSX файла"""
    if not await db.is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для выполнения этой команды.")
        await state.clear()
        return
    
    document = message.document
    
    # Проверяем, что это XLSX файл
    if not document.file_name.lower().endswith('.xlsx'):
        await message.answer(
            "❌ Неверный формат файла! Отправьте файл с расширением .xlsx"
        )
        return
    
    # Скачиваем файл
    try:
        # Создаем временную директорию
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, document.file_name)
            
            # Скачиваем файл
            await message.bot.download(document, file_path)
            
            # Проверяем структуру файла
            is_valid, error_message = schedule_parser.validate_xlsx_structure(file_path)
            
            if not is_valid:
                await message.answer(f"❌ Ошибка в структуре файла:\n{error_message}")
                return
            
            # Загружаем расписание
            if schedule_parser.load_xlsx_schedule(file_path):
                # Получаем статистику
                stats = schedule_parser.get_statistics()
                
                text = (
                    "✅ *Расписание успешно обновлено!*\n\n"
                    f"📊 *Статистика:*\n"
                    f"• Всего направлений: {stats.get('total_directions', 0)}\n"
                    f"• Преподавателей: {stats.get('total_teachers', 0)}\n"
                    f"• Кабинетов: {stats.get('total_cabinets', 0)}\n\n"
                    f"📅 *Занятия по дням:*\n"
                )
                
                for day, count in stats.get('days_with_lessons', {}).items():
                    text += f"• {day}: {count} направлений\n"
                
                text += "\n🔄 Расписание обновлено и готово к использованию!"
                
                builder = InlineKeyboardBuilder()
                builder.add(InlineKeyboardButton(text="📊 Подробная статистика", callback_data="schedule_statistics"))
                builder.add(InlineKeyboardButton(text="⬅️ Назад к настройкам расписания", callback_data="settings_schedule"))
                builder.adjust(1)
                
                await message.answer(
                    text,
                    parse_mode="Markdown",
                    reply_markup=builder.as_markup()
                )
            else:
                await message.answer("❌ Ошибка при загрузке расписания. Попробуйте еще раз.")
            
    except Exception as e:
        await message.answer(f"❌ Ошибка при обработке файла: {str(e)}")
    
    finally:
        await state.clear()

@schedule_router.callback_query(F.data == "schedule_statistics")
async def schedule_statistics_callback(callback: CallbackQuery):
    """Статистика расписания"""
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав для выполнения этой команды.", show_alert=True)
        return
    
    # Получаем статистику
    stats = schedule_parser.get_statistics()
    
    if not stats:
        text = "❌ Не удалось получить статистику расписания"
    else:
        text = (
            "📊 *Статистика расписания IT-Cube*\n\n"
            f"📚 *Общая информация:*\n"
            f"• Всего направлений: {stats.get('total_directions', 0)}\n"
            f"• Преподавателей: {stats.get('total_teachers', 0)}\n"
            f"• Кабинетов: {stats.get('total_cabinets', 0)}\n\n"
            f"📅 *Занятия по дням недели:*\n"
        )
        
        for day, count in stats.get('days_with_lessons', {}).items():
            text += f"• {day}: {count} направлений\n"
        
        # Получаем список всех направлений
        directions = schedule_parser.get_directions()
        if directions:
            text += f"\n📋 *Список направлений:*\n"
            for i, direction in enumerate(directions[:10], 1):  # Показываем первые 10
                text += f"{i}. {direction}\n"
            
            if len(directions) > 10:
                text += f"... и еще {len(directions) - 10} направлений"
    
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="⬅️ Назад к настройкам расписания", callback_data="settings_schedule"))
    
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@schedule_router.callback_query(F.data == "schedule_reload_csv")
async def schedule_reload_csv_callback(callback: CallbackQuery):
    """Обновление расписания из CSV файла"""
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав для выполнения этой команды.", show_alert=True)
        return
    
    try:
        # Перезагружаем расписание из CSV
        schedule_parser.load_schedule()
        
        # Получаем статистику
        stats = schedule_parser.get_statistics()
        
        text = (
            "🔄 *Расписание обновлено из CSV файла!*\n\n"
            f"📊 *Статистика:*\n"
            f"• Всего направлений: {stats.get('total_directions', 0)}\n"
            f"• Преподавателей: {stats.get('total_teachers', 0)}\n"
            f"• Кабинетов: {stats.get('total_cabinets', 0)}\n\n"
            "✅ Данные успешно обновлены!"
        )
        
        builder = InlineKeyboardBuilder()
        builder.add(InlineKeyboardButton(text="📊 Подробная статистика", callback_data="schedule_statistics"))
        builder.add(InlineKeyboardButton(text="⬅️ Назад к настройкам расписания", callback_data="settings_schedule"))
        builder.adjust(1)
        
        await callback.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=builder.as_markup()
        )
        
    except Exception as e:
        await callback.message.edit_text(
            f"❌ Ошибка при обновлении расписания: {str(e)}",
            reply_markup=get_schedule_settings_keyboard()
        )
    
    await callback.answer()

# Обработчик для любого текста в состоянии ожидания файла
@schedule_router.message(ScheduleStates.waiting_for_xlsx_file)
async def handle_text_in_xlsx_state(message: Message):
    """Обработка текста в состоянии ожидания XLSX файла"""
    await message.answer(
        "📤 Пожалуйста, отправьте файл Excel (.xlsx) с расписанием.\n\n"
        "Или нажмите ❌ Отменить загрузку для возврата к настройкам."
    )
