"""
Хендлеры для групповых чатов (публичных и админских)
"""
import asyncio
import aiosqlite
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

from database import db
from chat_handler import ChatType, ChatBehavior
from enhanced_keyboards import (
    get_public_group_keyboard, get_admin_group_keyboard, 
    get_quick_schedule_keyboard, get_admin_requests_keyboard,
    get_statistics_keyboard
)
from keyboards import (
    get_schedule_directions_keyboard, get_back_to_directions_keyboard, 
    get_direction_days_keyboard, get_schedule_directions_keyboard_for_groups,
    get_back_to_directions_keyboard_for_groups
)
from schedule_parser import schedule_parser

group_router = Router()

def escape_markdown(text: str) -> str:
    """Экранирует специальные символы Markdown"""
    if not text:
        return ""
    return text.replace('_', r'\_').replace('*', r'\*').replace('[', r'\[').replace(']', r'\]').replace('`', r'\`')

# Публичные группы

@group_router.message(Command("start"), F.chat.type.in_({"group", "supergroup"}))
async def group_start_command(message: Message):
    """Команда /start в группах"""
    chat_type = await ChatBehavior.determine_chat_type(message)
    
    welcome_text = ChatBehavior.get_welcome_message(
        chat_type, 
        message.from_user.first_name,
        message.chat.title
    )
    
    # Получаем username бота для кнопки обратной связи
    bot_info = await message.bot.get_me()
    bot_username = bot_info.username
    
    if chat_type == ChatType.PUBLIC_GROUP:
        keyboard = get_public_group_keyboard(bot_username)
    elif chat_type == ChatType.ADMIN_GROUP:
        keyboard = get_admin_group_keyboard()
    else:
        keyboard = get_public_group_keyboard(bot_username)
    
    await message.answer(welcome_text, parse_mode="Markdown", reply_markup=keyboard)

@group_router.callback_query(F.data == "schedule")
async def schedule_callback(callback: CallbackQuery):
    """Просмотр расписания в группе"""
    await callback.message.edit_text(
        "📅 *Выберите направление для просмотра расписания:*",
        parse_mode="Markdown",
        reply_markup=get_schedule_directions_keyboard_for_groups()
    )
    await callback.answer()

@group_router.callback_query(F.data == "quick_schedule")
async def quick_schedule_callback(callback: CallbackQuery):
    """Быстрый просмотр расписания в группе"""
    await callback.message.edit_text(
        "📅 *Быстрый просмотр расписания*\n\n"
        "Выберите, что хотите посмотреть:",
        parse_mode="Markdown",
        reply_markup=get_quick_schedule_keyboard()
    )
    await callback.answer()

@group_router.callback_query(F.data == "schedule_all")
async def schedule_all_directions_callback(callback: CallbackQuery):
    """Показать все направления для выбора расписания в группе"""
    await callback.message.edit_text(
        "📅 *Выберите направление для просмотра расписания:*",
        parse_mode="Markdown",
        reply_markup=get_schedule_directions_keyboard_for_groups()
    )
    await callback.answer()

@group_router.callback_query(F.data == "schedule_today")
async def schedule_today_callback(callback: CallbackQuery):
    """Расписание на сегодня"""
    today = datetime.now().strftime("%A").lower()
    day_mapping = {
        'monday': 'Понедельник',
        'tuesday': 'Вторник', 
        'wednesday': 'Среда',
        'thursday': 'Четверг',
        'friday': 'Пятница',
        'saturday': 'Суббота',
        'sunday': 'Воскресенье'
    }
    
    today_ru = day_mapping.get(today, 'Понедельник')
    schedule_text = await get_today_schedule(today_ru)
    
    await callback.message.edit_text(
        schedule_text,
        parse_mode="Markdown",
        reply_markup=get_back_to_quick_schedule_keyboard()
    )
    await callback.answer()

@group_router.callback_query(F.data == "schedule_tomorrow")
async def schedule_tomorrow_callback(callback: CallbackQuery):
    """Расписание на завтра"""
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%A").lower()
    day_mapping = {
        'monday': 'Понедельник',
        'tuesday': 'Вторник', 
        'wednesday': 'Среда',
        'thursday': 'Четверг',
        'friday': 'Пятница',
        'saturday': 'Суббота',
        'sunday': 'Воскресенье'
    }
    
    tomorrow_ru = day_mapping.get(tomorrow, 'Понедельник')
    schedule_text = await get_today_schedule(tomorrow_ru, "завтра")
    
    await callback.message.edit_text(
        schedule_text,
        parse_mode="Markdown",
        reply_markup=get_back_to_quick_schedule_keyboard()
    )
    await callback.answer()

@group_router.callback_query(F.data == "feedback_link")
async def feedback_link_fallback(callback: CallbackQuery):
    """Fallback для кнопки обратной связи, если username бота недоступен"""
    text = (
        "💬 *Обратная связь*\n\n"
        "Чтобы оставить обратную связь или задать вопрос преподавателю:\n\n"
        "1️⃣ Найдите этого бота в поиске Telegram\n"
        "2️⃣ Напишите ему в личные сообщения\n"
        "3️⃣ Выберите 'Обратная связь' в меню\n\n"
        "📝 В личных сообщениях доступен полный функционал бота!"
    )
    
    await callback.message.edit_text(text, parse_mode="Markdown")
    await callback.answer()

@group_router.callback_query(F.data == "bot_info")
async def bot_info_callback(callback: CallbackQuery):
    """Информация о боте"""
    text = (
        "🤖 *IT-Cube Bot*\n\n"
        "📚 *Этот бот предназначен для просмотра расписания занятий.*\n"
        "• Вы можете узнать расписание по направлениям прямо в группе.\n"
        "• Для получения ID чата используйте соответствующую кнопку.\n\n"
        "💬 *Если вы хотите оставить обратную связь или задать вопрос преподавателю — напишите боту в личные сообщения!*"
    )
    
    # Создаем клавиатуру с кнопкой возврата
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_group_menu"))
    
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=builder.as_markup())
    await callback.answer()

# Обработчики расписания для групп

@group_router.callback_query(F.data.startswith("dir:"))
async def group_show_direction_schedule(callback: CallbackQuery):
    """Показать расписание направления в группе"""
    direction_idx = int(callback.data.split(":", 1)[1])
    directions = schedule_parser.get_directions()
    
    if direction_idx >= len(directions):
        await callback.answer("❌ Направление не найдено", show_alert=True)
        return
    
    direction = directions[direction_idx]
    info = schedule_parser.get_direction_info(direction)
    
    # Формируем сообщение с информацией о направлении
    text = f"📚 *{direction}*\n\n"
    text += f"👨‍🏫 *Преподаватель:* {info.get('преподаватель', 'Не указан')}\n"
    text += f"🏢 *Кабинет:* {info.get('кабинет', 'Не указан')}\n\n"
    text += "Выберите действие:"
    
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_direction_days_keyboard(direction_idx)
    )
    await callback.answer()

@group_router.callback_query(F.data.startswith("full:"))
async def group_show_full_schedule(callback: CallbackQuery):
    """Полное расписание направления в группе"""
    direction_idx = int(callback.data.split(":", 1)[1])
    directions = schedule_parser.get_directions()
    
    if direction_idx >= len(directions):
        await callback.answer("❌ Направление не найдено", show_alert=True)
        return
    
    direction = directions[direction_idx]
    schedule_text = schedule_parser.format_direction_schedule(direction)
    
    await callback.message.edit_text(
        schedule_text,
        parse_mode="Markdown",
        reply_markup=get_back_to_directions_keyboard_for_groups()
    )
    await callback.answer()

@group_router.callback_query(F.data.startswith("day:"))
async def group_show_day_schedule(callback: CallbackQuery):
    """Расписание на день в группе"""
    parts = callback.data.split(":", 2)
    direction_idx = int(parts[1])
    short_day = parts[2]
    
    # Маппинг коротких названий дней обратно к полным
    day_reverse_mapping = {
        'пн': 'Понедельник', 'вт': 'Вторник', 'ср': 'Среда',
        'чт': 'Четверг', 'пт': 'Пятница', 'сб': 'Суббота'
    }
    day = day_reverse_mapping.get(short_day, short_day)
    
    directions = schedule_parser.get_directions()
    if direction_idx >= len(directions):
        await callback.answer("❌ Направление не найдено", show_alert=True)
        return
    
    direction = directions[direction_idx]
    info = schedule_parser.get_direction_info(direction)
    
    if day in info.get('дни', {}):
        schedule = info['дни'][day]
        text = f"📚 *{direction}*\n"
        text += f"👨‍🏫 *Преподаватель:* {info['преподаватель']}\n"
        text += f"🏢 *Кабинет:* {info['кабинет']}\n\n"
        text += f"📅 *{day}:*\n"
        for group_schedule in schedule:
            text += f"• {group_schedule}\n"
    else:
        text = f"В {day} занятий по направлению '{direction}' нет"
    
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_back_to_directions_keyboard_for_groups()
    )
    await callback.answer()

@group_router.callback_query(F.data == "back_to_directions")
async def group_back_to_directions(callback: CallbackQuery):
    """Назад к направлениям в группе"""
    await callback.message.edit_text(
        "📅 *Выберите направление для просмотра расписания:*",
        parse_mode="Markdown",
        reply_markup=get_schedule_directions_keyboard_for_groups()
    )
    await callback.answer()

@group_router.callback_query(F.data == "back_to_group_menu")
async def back_to_group_menu(callback: CallbackQuery):
    """Возврат в главное меню группы"""
    chat_type = await ChatBehavior.determine_chat_type(callback.message)
    
    welcome_text = ChatBehavior.get_welcome_message(
        chat_type, 
        callback.from_user.first_name,
        callback.message.chat.title
    )
    
    # Получаем username бота для кнопки обратной связи
    bot_info = await callback.bot.get_me()
    bot_username = bot_info.username
    
    if chat_type == ChatType.PUBLIC_GROUP:
        keyboard = get_public_group_keyboard(bot_username)
    elif chat_type == ChatType.ADMIN_GROUP:
        keyboard = get_admin_group_keyboard()
    else:
        keyboard = get_public_group_keyboard(bot_username)
    
    await callback.message.edit_text(welcome_text, parse_mode="Markdown", reply_markup=keyboard)
    await callback.answer()

# Админские группы

@group_router.callback_query(F.data == "active_requests")
async def admin_active_requests(callback: CallbackQuery):
    """Активные заявки для админской группы"""
    # Проверяем, что это админская группа
    chat_type = await ChatBehavior.determine_chat_type(callback.message)
    if chat_type != ChatType.ADMIN_GROUP:
        await callback.answer("❌ Доступно только в админских группах", show_alert=True)
        return
    
    # Получаем активные заявки
    active_requests = await get_active_requests_summary()
    
    # Проверяем, что получили корректный текст
    if not active_requests:
        active_requests = "📊 Активных заявок нет"
    
    text = (
        "🎫 *Активные заявки*\n\n"
        f"{active_requests}\n\n"
        "💡 Для ответа на заявку используйте reply на уведомление или команду /msg ID\\_пользователя в ЛС бота."
    )
    
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_admin_requests_keyboard()
    )
    await callback.answer()

@group_router.callback_query(F.data == "group_statistics")
async def group_statistics_callback(callback: CallbackQuery):
    """Меню статистики для группы"""
    # Для callback-запросов нужно проверять права пользователя напрямую
    is_admin = await db.is_admin(callback.from_user.id)
    if not is_admin:
        await callback.answer("❌ Доступно только администраторам", show_alert=True)
        return
    
    chat_type = await ChatBehavior.determine_chat_type(callback.message)
    
    text = (
        "📊 *Статистика IT-Cube Bot*\n\n"
        "Выберите тип статистики:"
    )
    
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_statistics_keyboard(chat_type)
    )
    await callback.answer()

# Обработчики статистики для групп

@group_router.callback_query(F.data == "stats_general")
async def group_stats_general_callback(callback: CallbackQuery):
    """Общая статистика для группы"""
    print(f"[DEBUG] group_stats_general_callback вызвана пользователем {callback.from_user.id}")
    
    # Для callback-запросов нужно проверять права пользователя напрямую
    is_admin = await db.is_admin(callback.from_user.id)
    print(f"[DEBUG] is_admin для пользователя {callback.from_user.id}: {is_admin}")
    
    chat_type = await ChatBehavior.determine_chat_type(callback.message)
    print(f"[DEBUG] Определен тип чата для статистики: {chat_type}")
    
    # Проверяем права: должен быть администратор И (админская группа ИЛИ личный чат)
    if not is_admin:
        print(f"[DEBUG] Пользователь не является администратором")
        await callback.answer("❌ Доступно только администраторам", show_alert=True)
        return
    
    if chat_type not in [ChatType.ADMIN_GROUP, ChatType.PRIVATE_ADMIN, ChatType.PRIVATE_USER]:
        print(f"[DEBUG] Неподходящий тип чата: {chat_type}")
        await callback.answer("❌ Доступно только в личных сообщениях или админских группах", show_alert=True)
        return
    
    print(f"[DEBUG] Доступ разрешен, продолжаем выполнение")
    
    from admin_handlers import get_general_statistics
    stats = await get_general_statistics()
    
    # Создаем клавиатуру с кнопкой возврата в зависимости от типа чата
    if chat_type == ChatType.ADMIN_GROUP:
        builder = InlineKeyboardBuilder()
        builder.add(InlineKeyboardButton(text="⬅️ Назад к статистике", callback_data="group_statistics"))
        reply_markup = builder.as_markup()
    else:  # PRIVATE_ADMIN - без кнопки возврата
        reply_markup = None
    
    await callback.message.edit_text(
        stats,
        parse_mode="Markdown",
        reply_markup=reply_markup
    )
    await callback.answer()

@group_router.callback_query(F.data == "stats_requests")
async def group_stats_requests_callback(callback: CallbackQuery):
    """Статистика заявок для группы"""
    # Для callback-запросов нужно проверять права пользователя напрямую
    is_admin = await db.is_admin(callback.from_user.id)
    if not is_admin:
        await callback.answer("❌ Доступно только администраторам", show_alert=True)
        return
    
    chat_type = await ChatBehavior.determine_chat_type(callback.message)
    
    from admin_handlers import get_requests_statistics
    stats = await get_requests_statistics()
    
    # Создаем клавиатуру с кнопкой возврата в зависимости от типа чата
    if chat_type == ChatType.ADMIN_GROUP:
        builder = InlineKeyboardBuilder()
        builder.add(InlineKeyboardButton(text="⬅️ Назад к статистике", callback_data="group_statistics"))
        reply_markup = builder.as_markup()
    else:  # PRIVATE_ADMIN - без кнопки возврата
        reply_markup = None
    
    await callback.message.edit_text(
        stats,
        parse_mode="Markdown",
        reply_markup=reply_markup
    )
    await callback.answer()

@group_router.callback_query(F.data == "stats_users")
async def group_stats_users_callback(callback: CallbackQuery):
    """Статистика пользователей для группы"""
    # Для callback-запросов нужно проверять права пользователя напрямую
    is_admin = await db.is_admin(callback.from_user.id)
    if not is_admin:
        await callback.answer("❌ Доступно только администраторам", show_alert=True)
        return
    
    chat_type = await ChatBehavior.determine_chat_type(callback.message)
    
    from admin_handlers import get_users_statistics
    stats = await get_users_statistics()
    
    # Создаем клавиатуру с кнопкой возврата в зависимости от типа чата
    if chat_type == ChatType.ADMIN_GROUP:
        builder = InlineKeyboardBuilder()
        builder.add(InlineKeyboardButton(text="⬅️ Назад к статистике", callback_data="group_statistics"))
        reply_markup = builder.as_markup()
    else:  # PRIVATE_ADMIN - без кнопки возврата
        reply_markup = None
    
    await callback.message.edit_text(
        stats,
        parse_mode="Markdown",
        reply_markup=reply_markup
    )
    await callback.answer()

@group_router.callback_query(F.data == "stats_directions")
async def group_stats_directions_callback(callback: CallbackQuery):
    """Статистика по направлениям для группы"""
    # Для callback-запросов нужно проверять права пользователя напрямую
    is_admin = await db.is_admin(callback.from_user.id)
    if not is_admin:
        await callback.answer("❌ Доступно только администраторам", show_alert=True)
        return
    
    chat_type = await ChatBehavior.determine_chat_type(callback.message)
    
    from admin_handlers import get_directions_statistics
    stats = await get_directions_statistics()
    
    # Создаем клавиатуру с кнопкой возврата в зависимости от типа чата
    if chat_type == ChatType.ADMIN_GROUP:
        builder = InlineKeyboardBuilder()
        builder.add(InlineKeyboardButton(text="⬅️ Назад к статистике", callback_data="group_statistics"))
        reply_markup = builder.as_markup()
    else:  # PRIVATE_ADMIN - без кнопки возврата
        reply_markup = None
    
    await callback.message.edit_text(
        stats,
        parse_mode="Markdown",
        reply_markup=reply_markup
    )
    await callback.answer()

@group_router.callback_query(F.data == "group_settings")
async def group_settings_callback(callback: CallbackQuery):
    """Настройки группы"""
    chat_type = await ChatBehavior.determine_chat_type(callback.message)
    if chat_type != ChatType.ADMIN_GROUP:
        await callback.answer("❌ Доступно только в админских группах", show_alert=True)
        return
    
    chat_id = callback.message.chat.id
    is_active = await db.is_notification_chat(chat_id)
    
    text = (
        f"⚙️ *Настройки группы*\n\n"
        f"🆔 *ID чата:* `{chat_id}`\n"
        f"📊 *Статус уведомлений:* {'🔔 Включены' if is_active else '🔇 Отключены'}\n\n"
        f"💡 Для изменения настроек обратитесь к администратору бота в личных сообщениях."
    )
    
    await callback.message.edit_text(text, parse_mode="Markdown")
    await callback.answer()

# Вспомогательные функции

async def get_today_schedule(day: str, day_name: str = "сегодня") -> str:
    """Получить расписание на указанный день"""
    directions = schedule_parser.get_directions()
    
    if not directions:
        return f"📅 *Расписание на {day_name}*\n\n❌ Расписание не загружено."
    
    schedule_text = f"📅 *Расписание на {day_name} ({day})*\n\n"
    
    has_classes = False
    for direction in directions:
        info = schedule_parser.get_direction_info(direction)
        if day in info.get('дни', {}):
            has_classes = True
            schedule = info['дни'][day]
            schedule_text += f"📚 *{direction}*\n"
            schedule_text += f"👨‍🏫 {info.get('преподаватель', 'Не указан')}\n"
            schedule_text += f"🏢 {info.get('кабинет', 'Не указан')}\n"
            
            for group_schedule in schedule:
                schedule_text += f"• {group_schedule}\n"
            schedule_text += "\n"
    
    if not has_classes:
        schedule_text += f"😴 В {day.lower()} занятий нет.\nОтличный день для отдыха!"
    
    return schedule_text

async def get_active_requests_summary() -> str:
    """Получить краткую сводку активных заявок"""
    try:
        # Получаем активные заявки из базы данных
        async with aiosqlite.connect(db.db_path) as conn:
            cursor = await conn.execute('''
                SELECT COUNT(*) as total,
                       COUNT(CASE WHEN created_at > datetime('now', '-1 day') THEN 1 END) as today,
                       COUNT(CASE WHEN created_at > datetime('now', '-1 hour') THEN 1 END) as hour
                FROM feedback_messages 
                WHERE status = 'active'
            ''')
            stats = await cursor.fetchone()
            
            if not stats:
                return "📊 Активных заявок нет"
            
            total, today, hour = stats
            
            text = f"📊 *Всего активных:* {total}\n"
            text += f"📅 *За сегодня:* {today}\n"
            text += f"🕐 *За час:* {hour}\n"
            
            if total == 0:
                text += "\n✅ Все заявки обработаны!"
            elif hour > 5:
                text += "\n⚠️ Много новых заявок за последний час!"
            
            return text
            
    except Exception as e:
        # Экранируем специальные символы Markdown в сообщении об ошибке
        error_msg = escape_markdown(str(e))
        return f"❌ Ошибка получения статистики: {error_msg}"

async def get_group_statistics() -> str:
    """Получить статистику для группы"""
    try:
        async with aiosqlite.connect(db.db_path) as conn:
            # Общая статистика заявок
            cursor = await conn.execute('''
                SELECT 
                    COUNT(*) as total_requests,
                    COUNT(CASE WHEN status = 'active' THEN 1 END) as active_requests,
                    COUNT(CASE WHEN status = 'closed' THEN 1 END) as closed_requests,
                    COUNT(CASE WHEN created_at > datetime('now', '-7 days') THEN 1 END) as week_requests
                FROM feedback_messages
            ''')
            request_stats = await cursor.fetchone()
            
            # Статистика пользователей
            cursor = await conn.execute('''
                SELECT COUNT(DISTINCT user_id) as unique_users
                FROM feedback_messages
                WHERE created_at > datetime('now', '-30 days')
            ''')
            user_stats = await cursor.fetchone()
            
            if not request_stats:
                return "❌ Не удалось получить статистику"
            
            total, active, closed, week = request_stats
            unique_users = user_stats[0] if user_stats else 0
            
            text = "📊 *Статистика IT-Cube Bot*\n\n"
            text += f"🎫 *Заявки:*\n"
            text += f"• Всего: {total}\n"
            text += f"• Активных: {active}\n"
            text += f"• Закрытых: {closed}\n"
            text += f"• За неделю: {week}\n\n"
            text += f"👥 *Пользователи:*\n"
            text += f"• Уникальных за месяц: {unique_users}\n\n"
            
            if active > 0:
                response_rate = round((closed / total) * 100, 1) if total > 0 else 0
                text += f"📈 *Процент ответов:* {response_rate}%"
            else:
                text += "✅ *Все заявки обработаны!*"
            
            return text
            
    except Exception as e:
        # Экранируем специальные символы Markdown в сообщении об ошибке
        error_msg = escape_markdown(str(e))
        return f"❌ Ошибка получения статистики: {error_msg}"

def get_back_to_quick_schedule_keyboard():
    """Кнопка возврата к быстрому расписанию"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="⬅️ Назад", callback_data="quick_schedule"))
    return builder.as_markup()

# Обработка команды /menu в группах
@group_router.message(F.text == "/menu", F.chat.type.in_({"group", "supergroup"}))
async def handle_menu_command(message: Message):
    """Обработка команды /menu в группах"""
    chat_type = await ChatBehavior.determine_chat_type(message)
    
    welcome_text = ChatBehavior.get_welcome_message(
        chat_type, 
        message.from_user.first_name,
        message.chat.title
    )
    
    # Получаем username бота для кнопки обратной связи
    bot_info = await message.bot.get_me()
    bot_username = bot_info.username
    
    if chat_type == ChatType.PUBLIC_GROUP:
        keyboard = get_public_group_keyboard(bot_username)
    elif chat_type == ChatType.ADMIN_GROUP:
        keyboard = get_admin_group_keyboard()
    else:
        keyboard = get_public_group_keyboard(bot_username)
    
    await message.reply(welcome_text, parse_mode="Markdown", reply_markup=keyboard)

# Обработка ответов администраторов на заявки в групповых чатах
@group_router.message(F.reply_to_message & F.chat.type.in_({"group", "supergroup"}))
async def handle_admin_reply_in_group(message: Message):
    """Обработка ответов администраторов на заявки в групповых чатах через reply"""
    import re
    from enhanced_keyboards import get_admin_keyboard, get_teacher_keyboard
    
    # Проверяем, что это reply на сообщение бота
    if not message.reply_to_message or message.reply_to_message.from_user.id != message.bot.id:
        return
    
    # Проверяем, что отвечающий - админ или преподаватель
    is_admin = await db.is_admin(message.from_user.id)
    is_teacher = await db.is_teacher(message.from_user.id)
    
    if not (is_admin or is_teacher):
        return
    
    # Проверяем, что это админская группа
    chat_type = await ChatBehavior.determine_chat_type(message)
    if chat_type != ChatType.ADMIN_GROUP:
        return
    
    # Ищем номер заявки в тексте сообщения, на которое отвечают
    reply_text = message.reply_to_message.text or ""
    match = re.search(r'#(\d+)', reply_text)
    if not match:
        await message.reply("❌ Не удалось найти номер заявки для ответа.")
        return
    
    message_id = int(match.group(1))
    reply_content = message.text
    
    # Получаем исходную заявку
    feedback_msg = await db.get_feedback_message(message_id)
    if not feedback_msg:
        await message.reply(f"❌ Заявка #{message_id} не найдена.")
        return
    
    user_id = feedback_msg[1]
    original_text = feedback_msg[4]
    is_answered = feedback_msg[6]
    status = feedback_msg[7] if len(feedback_msg) > 7 else 'active'
    
    # Проверяем, что заявка ещё активна
    if status == 'closed' or is_answered:
        await message.reply(f"⚠️ Заявка #{message_id} уже закрыта.")
        return
    
    # Если отвечает преподаватель, проверяем права на данную заявку
    if is_teacher and not is_admin:
        can_reply = await db.can_teacher_reply_to_request(message.from_user.id, message_id)
        if not can_reply:
            await message.reply(
                f"❌ У вас нет прав для ответа на заявку #{message_id}.\n"
                "Вы можете отвечать только на заявки по направлениям, к которым вы привязаны."
            )
            return
    
    try:
        # Определяем роль отвечающего
        if is_admin and not is_teacher:
            responder_role = "Администратор"
        elif is_teacher:
            responder_role = "Преподаватель"
        else:
            responder_role = "Администратор"  # по умолчанию
        
        user_reply = (
            f"✅ *Ответ на вашу заявку #{message_id}*\n\n"
            f"👤 *Ответил:* {responder_role}\n"
            f"📋 *Статус:* Заявка закрыта\n\n"
            f"💬 *Ваша заявка:*\n{original_text}\n\n"
            f"📝 *Ответ:*\n{reply_content}\n\n"
            f"💡 Теперь вы можете создать новую заявку, если это необходимо."
        )
        
        await message.bot.send_message(user_id, user_reply, parse_mode="Markdown")
        await db.mark_message_answered(message_id, message.from_user.id, reply_content)
        
        # Обновляем статус в админских уведомлениях
        await db.update_notification_status(message.bot, message_id, f"Закрыта ({responder_role})", reply_content)
        
        # Отправляем уведомления преподавателям о закрытии заявки
        await db.notify_teachers_about_closed_request(message.bot, message_id, responder_role, reply_content)
        
        await message.reply(
            f"✅ Ответ на заявку #{message_id} отправлен! Заявка закрыта."
        )
        
    except Exception as e:
        await message.reply(
            f"❌ Ошибка отправки ответа: {str(e)}"
        )

# Обработка упоминаний бота в группах
@group_router.message(F.text.contains("@") & F.chat.type.in_({"group", "supergroup"}))
async def handle_bot_mention(message: Message):
    """Обработка упоминания бота в группах"""
    # Проверяем, упомянут ли бот
    bot_info = await message.bot.get_me()
    bot_username = bot_info.username
    
    if f"@{bot_username}" in message.text.lower():
        chat_type = await ChatBehavior.determine_chat_type(message)
        
        # Простые ответы на упоминания
        if "расписание" in message.text.lower():
            await message.reply(
                "📅 Для просмотра расписания используйте кнопки ниже или напишите мне в ЛС!",
                reply_markup=get_schedule_directions_keyboard_for_groups()
            )
        elif "помощь" in message.text.lower() or "help" in message.text.lower():
            help_text = (
                "🤖 *Доступные команды в группе:*\n\n"
                "• `/start` - показать меню\n"
                "• `/menu` - быстрый вызов меню\n"
                "• `/chatid` - показать ID чата\n"
                "• Упомяните меня с словом 'расписание' для быстрого доступа\n\n"
                "💬 *Для полного функционала напишите мне в личные сообщения!*"
            )
            await message.reply(help_text, parse_mode="Markdown")
        else:
            await message.reply(
                "👋 Привет! Я бот IT-Cube.\n"
                "💬 Напишите мне в личные сообщения для доступа ко всем функциям!"
            )
