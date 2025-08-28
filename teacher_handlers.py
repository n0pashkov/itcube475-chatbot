"""
Хендлеры для преподавателей
"""
import aiosqlite
from datetime import datetime
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

from database import db
from chat_handler import ChatType, ChatBehavior, require_permission
from enhanced_keyboards import get_teacher_requests_keyboard
from schedule_parser import schedule_parser

teacher_router = Router()

# Основные команды для преподавателей

@teacher_router.message(F.text == "🎫 Мои заявки")
@require_permission("my_requests")
async def teacher_my_requests(message: Message, **kwargs):
    """Заявки преподавателя"""
    teacher_id = message.from_user.id
    
    # Получаем заявки для преподавателя
    my_requests = await db.get_teacher_requests(teacher_id)
    
    if not my_requests:
        text = (
            "🎫 *Ваши заявки*\n\n"
            "✅ У вас нет активных заявок!\n\n"
            "💡 Заявки будут появляться здесь, когда студенты обратятся по вашим направлениям."
        )
        await message.answer(text, parse_mode="Markdown")
        return
    
    text = f"🎫 *Ваши активные заявки* ({len(my_requests)})\n\n"
    
    for request in my_requests[:10]:  # Показываем первые 10
        msg_id, user_id, username, first_name, msg_text, created_at, status, direction_name = request
        
        created_date = datetime.fromisoformat(created_at).strftime("%d.%m %H:%M")
        user_display = f"@{username}" if username else f"{first_name} (ID{user_id})"
        short_message = msg_text[:60] + "..." if len(msg_text) > 60 else msg_text
        short_message = escape_markdown(short_message)
        
        text += f"📝 *#{msg_id}* ({created_date})\n"
        text += f"👤 {user_display}\n"
        text += f"📚 {direction_name}\n"
        text += f"💬 {short_message}\n\n"
    
    if len(my_requests) > 10:
        text += f"... и еще {len(my_requests) - 10} заявок\n\n"
    
    text += "💡 *Для ответа:* сделайте reply на уведомление о заявке или используйте /msg ID_пользователя"
    
    # Добавляем кнопки управления
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="📊 Статистика", callback_data=f"teacher_stats:{teacher_id}"))
    builder.add(InlineKeyboardButton(text="📚 Мои направления", callback_data=f"teacher_directions:{teacher_id}"))
    builder.adjust(2)
    
    await message.answer(text, parse_mode="Markdown", reply_markup=builder.as_markup())

@teacher_router.message(F.text == "📚 Мои направления")
@require_permission("my_requests")
async def teacher_my_directions(message: Message, **kwargs):
    """Направления преподавателя"""
    teacher_id = message.from_user.id
    
    # Получаем направления преподавателя
    directions = await db.get_directions_for_teacher(teacher_id)
    
    if not directions:
        text = (
            "📚 *Ваши направления*\n\n"
            "❌ У вас нет привязанных направлений.\n\n"
            "💡 Обратитесь к администратору для назначения направлений."
        )
        await message.answer(text, parse_mode="Markdown")
        return
    
    text = f"📚 *Ваши направления* ({len(directions)})\n\n"
    
    for direction_id, direction_name in directions:
        # Получаем информацию о направлении из расписания
        direction_info = schedule_parser.get_direction_info(direction_name)
        
        text += f"📖 *{direction_name}*\n"
        
        if direction_info:
            cabinet = direction_info.get('кабинет', 'Не указан')
            days = list(direction_info.get('дни', {}).keys())
            text += f"🏢 Кабинет: {cabinet}\n"
            if days:
                text += f"📅 Дни: {', '.join(days)}\n"
        
        # Получаем количество активных заявок по направлению
        active_count = await get_active_requests_count_for_direction(direction_id)
        if active_count > 0:
            text += f"🎫 Активных заявок: {active_count}\n"
        
        text += "\n"
    
    text += "💡 Расписание обновляется автоматически из файла rasp.csv"
    
    # Добавляем кнопки для каждого направления
    builder = InlineKeyboardBuilder()
    for direction_id, direction_name in directions[:5]:  # Первые 5 направлений
        short_name = direction_name[:20] + "..." if len(direction_name) > 20 else direction_name
        builder.add(InlineKeyboardButton(
            text=f"📖 {short_name}",
            callback_data=f"direction_detail:{direction_id}"
        ))
    builder.adjust(1)
    
    await message.answer(text, parse_mode="Markdown", reply_markup=builder.as_markup())

# Callback handlers

@teacher_router.callback_query(F.data.startswith("teacher_stats:"))
async def teacher_statistics(callback: CallbackQuery):
    """Статистика преподавателя"""
    teacher_id = int(callback.data.split(":")[1])
    
    # Проверяем права доступа
    if callback.from_user.id != teacher_id and not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    stats = await get_teacher_statistics(teacher_id)
    
    await callback.message.edit_text(
        stats,
        parse_mode="Markdown"
    )
    await callback.answer()

@teacher_router.callback_query(F.data.startswith("teacher_directions:"))
async def teacher_directions_detail(callback: CallbackQuery):
    """Подробная информация о направлениях преподавателя"""
    teacher_id = int(callback.data.split(":")[1])
    
    if callback.from_user.id != teacher_id and not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    directions = await db.get_directions_for_teacher(teacher_id)
    
    if not directions:
        text = "📚 *Направления не назначены*"
    else:
        text = f"📚 *Направления преподавателя*\n\n"
        
        for direction_id, direction_name in directions:
            # Статистика по направлению
            total_requests = await get_total_requests_for_direction(direction_id)
            active_requests = await get_active_requests_count_for_direction(direction_id)
            
            text += f"📖 *{direction_name}*\n"
            text += f"🎫 Всего заявок: {total_requests}\n"
            text += f"🔓 Активных: {active_requests}\n\n"
    
    # Кнопка назад
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"teacher_requests:{teacher_id}"))
    
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@teacher_router.callback_query(F.data.startswith("direction_detail:"))
async def direction_detail(callback: CallbackQuery):
    """Подробная информация о направлении"""
    direction_id = int(callback.data.split(":")[1])
    
    # Получаем направление
    direction = await db.get_direction_by_id(direction_id)
    if not direction:
        await callback.answer("❌ Направление не найдено", show_alert=True)
        return
    
    direction_name = direction[1]
    
    # Проверяем, что пользователь привязан к этому направлению
    user_directions = await db.get_directions_for_teacher(callback.from_user.id)
    if direction_id not in [d[0] for d in user_directions] and not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа к этому направлению", show_alert=True)
        return
    
    # Получаем информацию из расписания
    direction_info = schedule_parser.get_direction_info(direction_name)
    
    text = f"📖 *{direction_name}*\n\n"
    
    if direction_info:
        text += f"👨‍🏫 *Преподаватель:* {direction_info.get('преподаватель', 'Не указан')}\n"
        text += f"🏢 *Кабинет:* {direction_info.get('кабинет', 'Не указан')}\n\n"
        
        days = direction_info.get('дни', {})
        if days:
            text += "*📅 Расписание:*\n"
            for day, schedule in days.items():
                text += f"*{day}:*\n"
                for group_schedule in schedule:
                    text += f"• {group_schedule}\n"
                text += "\n"
    
    # Статистика заявок по направлению
    total_requests = await get_total_requests_for_direction(direction_id)
    active_requests = await get_active_requests_count_for_direction(direction_id)
    
    text += f"📊 *Статистика заявок:*\n"
    text += f"• Всего: {total_requests}\n"
    text += f"• Активных: {active_requests}\n"
    
    if active_requests > 0:
        text += f"\n💡 У вас есть {active_requests} активных заявок по этому направлению"
    
    await callback.message.edit_text(text, parse_mode="Markdown")
    await callback.answer()

# Команды для работы с заявками

@teacher_router.message(Command("my_requests"))
@require_permission("my_requests")
async def cmd_my_requests(message: Message, **kwargs):
    """Команда для просмотра заявок преподавателя"""
    await teacher_my_requests(message, **kwargs)

@teacher_router.message(Command("my_directions"))
@require_permission("my_requests")
async def cmd_my_directions(message: Message, **kwargs):
    """Команда для просмотра направлений преподавателя"""
    await teacher_my_directions(message, **kwargs)

# Вспомогательные функции

def escape_markdown(text: str) -> str:
    """Экранировать специальные символы markdown"""
    if not text:
        return ""
    
    # Экранируем только критичные markdown символы
    escape_chars = ['*', '_', '[', ']', '`']
    for char in escape_chars:
        text = text.replace(char, f'\\{char}')
    
    return text

async def get_teacher_statistics(teacher_id: int) -> str:
    """Получить статистику преподавателя"""
    try:
        # Получаем направления преподавателя
        directions = await db.get_directions_for_teacher(teacher_id)
        
        if not directions:
            return "📊 *Ваша статистика*\n\n❌ У вас нет назначенных направлений"
        
        direction_ids = [d[0] for d in directions]
        
        # Статистика заявок
        async with aiosqlite.connect(db.db_path) as conn:
            placeholders = ','.join(['?' for _ in direction_ids])
            
            cursor = await conn.execute(f'''
                SELECT 
                    COUNT(*) as total_requests,
                    COUNT(CASE WHEN status = 'active' THEN 1 END) as active_requests,
                    COUNT(CASE WHEN is_answered = 1 AND answered_by = ? THEN 1 END) as answered_by_me,
                    COUNT(CASE WHEN created_at > datetime('now', '-7 days') THEN 1 END) as week_requests
                FROM feedback_messages 
                WHERE direction_id IN ({placeholders})
            ''', [teacher_id] + direction_ids)
            
            stats = await cursor.fetchone()
            
            if not stats:
                return "📊 *Ваша статистика*\n\n❌ Данные не найдены"
            
            total, active, answered, week = stats
            
            text = "📊 *Ваша статистика*\n\n"
            text += f"📚 *Направлений:* {len(directions)}\n\n"
            text += f"🎫 *Заявки:*\n"
            text += f"• Всего по вашим направлениям: {total}\n"
            text += f"• Активных: {active}\n"
            text += f"• Отвечено вами: {answered}\n"
            text += f"• За неделю: {week}\n\n"
            
            if total > 0 and answered > 0:
                response_rate = round((answered / total) * 100, 1)
                text += f"📈 *Ваш процент ответов:* {response_rate}%\n\n"
            
            text += f"💡 *Направления:*\n"
            for _, direction_name in directions:
                short_name = direction_name[:30] + "..." if len(direction_name) > 30 else direction_name
                text += f"• {short_name}\n"
            
            return text
            
    except Exception as e:
        return f"❌ Ошибка получения статистики: {str(e)}"

async def get_active_requests_count_for_direction(direction_id: int) -> int:
    """Получить количество активных заявок для направления"""
    try:
        async with aiosqlite.connect(db.db_path) as conn:
            cursor = await conn.execute('''
                SELECT COUNT(*) FROM feedback_messages 
                WHERE direction_id = ? AND status = 'active'
            ''', (direction_id,))
            result = await cursor.fetchone()
            return result[0] if result else 0
    except Exception:
        return 0

async def get_total_requests_for_direction(direction_id: int) -> int:
    """Получить общее количество заявок для направления"""
    try:
        async with aiosqlite.connect(db.db_path) as conn:
            cursor = await conn.execute('''
                SELECT COUNT(*) FROM feedback_messages 
                WHERE direction_id = ?
            ''', (direction_id,))
            result = await cursor.fetchone()
            return result[0] if result else 0
    except Exception:
        return 0
