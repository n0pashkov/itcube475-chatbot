"""
Расширенные хендлеры для администраторов
"""
import asyncio
import aiosqlite
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

from database import db
from chat_handler import ChatType, ChatBehavior, require_permission
from enhanced_keyboards import (
    get_admin_requests_keyboard, get_statistics_keyboard, 
    get_settings_keyboard, get_quick_actions_for_request,
    get_request_detail_keyboard, get_working_hours_keyboard,
    get_day_working_hours_keyboard
)
from keyboards import (
    get_admin_management_keyboard, get_teacher_management_keyboard,
    get_notification_settings_keyboard
)

admin_router = Router()

def escape_markdown(text: str) -> str:
    """Экранирует специальные символы Markdown"""
    if not text:
        return ""
    return text.replace('_', r'\_').replace('*', r'\*').replace('[', r'\[').replace(']', r'\]').replace('`', r'\`')

# Состояния для админских функций
class AdminStates(StatesGroup):
    waiting_for_request_search = State()
    waiting_for_broadcast_message = State()
    waiting_for_request_reply = State()
    waiting_for_request_answer = State()
    waiting_for_working_hours_time = State()

# Основные админские команды

@admin_router.message(F.text == "🎫 Заявки")
@require_permission("view_requests")
async def admin_requests_menu(message: Message, **kwargs):
    """Меню работы с заявками"""
    text = (
        "🎫 *Управление заявками*\n\n"
        "Выберите действие:"
    )
    
    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=get_admin_requests_keyboard()
    )

@admin_router.message(F.text == "📊 Статистика")
@require_permission("statistics")
async def admin_statistics_menu(message: Message, **kwargs):
    """Меню статистики"""
    print(f"[DEBUG] admin_statistics_menu вызвана пользователем {message.from_user.id} ({message.from_user.first_name})")
    
    # Дополнительная проверка прав администратора для надежности
    is_admin = await db.is_admin(message.from_user.id)
    print(f"[DEBUG] is_admin для пользователя {message.from_user.id}: {is_admin}")
    
    if not is_admin:
        print(f"[DEBUG] Отправляем сообщение об отказе в доступе")
        await message.answer("❌ У вас нет прав для выполнения этой команды.")
        return
    
    print(f"[DEBUG] Права проверены успешно, продолжаем выполнение")
    chat_type = await ChatBehavior.determine_chat_type(message)
    
    text = (
        "📊 *Статистика IT-Cube Bot*\n\n"
        "Выберите тип статистики:"
    )
    
    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=get_statistics_keyboard(chat_type)
    )

@admin_router.message(F.text == "⚙️ Настройки")
@require_permission("admin_management")
async def admin_settings_menu(message: Message, **kwargs):
    """Меню настроек"""
    chat_type = await ChatBehavior.determine_chat_type(message)
    
    text = (
        "⚙️ *Настройки бота*\n\n"
        "Выберите раздел настроек:"
    )
    
    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=get_settings_keyboard(chat_type)
    )

# Обработка заявок

@admin_router.callback_query(F.data == "requests_active")
async def show_active_requests(callback: CallbackQuery):
    """Показать активные заявки с улучшенным интерфейсом"""
    active_requests = await get_active_requests_detailed()
    
    if not active_requests:
        text = "🎫 <b>Активные заявки</b>\n\n✅ Активных заявок нет!"
        keyboard = get_admin_requests_keyboard()
    else:
        text = "🎫 <b>Активные заявки</b>\n\n"
        builder = InlineKeyboardBuilder()
        
        for request in active_requests[:5]:  # Показываем только первые 5 для лучшего UX
            request_id, user_id, username, first_name, message_text, created_at, direction_name = request
            
            # Форматируем дату
            created_date = datetime.fromisoformat(created_at).strftime("%d.%m %H:%M")
            user_display = f"@{username}" if username else f"ID{user_id}"
            
            # Обрезаем длинные сообщения и экранируем HTML символы
            short_message = message_text[:40] + "..." if len(message_text) > 40 else message_text
            short_message = escape_html(short_message)
            
            text += f"📝 <b>#{request_id}</b> ({created_date})\n"
            text += f"👤 {user_display}\n"
            text += f"📚 {direction_name or 'Без направления'}\n"
            text += f"💬 {short_message}\n\n"
            
            # Добавляем кнопку для детального просмотра каждой заявки
            builder.add(InlineKeyboardButton(
                text=f"📝 #{request_id} - {user_display[:15]}",
                callback_data=f"request_detail:{request_id}"
            ))

        
        if len(active_requests) > 5:
            text += f"... и еще {len(active_requests) - 5} заявок\n\n"
            text += "💡 Нажмите на заявку для детального просмотра"
        
        # Добавляем кнопки управления
        builder.add(InlineKeyboardButton(text="🔄 Обновить", callback_data="requests_active"))
        builder.add(InlineKeyboardButton(text="⬅️ К меню заявок", callback_data="requests_menu"))
        
        builder.adjust(1)  # Каждая заявка на отдельной строке
        keyboard = builder.as_markup()
    
    # Проверяем, отличается ли новое содержимое от текущего
    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    except Exception as e:
        if "message is not modified" in str(e):
            # Если сообщение не изменилось, просто отвечаем на callback
            await callback.answer("✅ Список актуален")
        else:
            # Если другая ошибка, пробрасываем её дальше
            raise e
    else:
        await callback.answer()

@admin_router.callback_query(F.data == "requests_closed")
async def show_closed_requests(callback: CallbackQuery):
    """Показать закрытые заявки"""
    closed_requests = await get_closed_requests_summary()
    
    # Экранируем HTML символы в тексте статистики
    closed_requests_safe = escape_html(closed_requests)
    
    text = (
        "🔒 <b>Закрытые заявки</b>\n\n"
        f"{closed_requests_safe}\n\n"
        "💡 Используйте /msg ID_пользователя для просмотра истории"
    )
    
    await callback.message.edit_text(text, parse_mode="HTML")
    await callback.answer()

@admin_router.callback_query(F.data == "requests_search")
async def start_request_search(callback: CallbackQuery, state: FSMContext):
    """Начать поиск заявок по пользователю"""
    await callback.message.answer(
        "🔍 *Поиск заявок*\n\n"
        "Отправьте ID пользователя или username (с @) для поиска его заявок:",
        parse_mode="Markdown"
    )
    await state.set_state(AdminStates.waiting_for_request_search)
    await callback.answer()

@admin_router.message(StateFilter(AdminStates.waiting_for_request_search))
async def process_request_search(message: Message, state: FSMContext):
    """Обработать поиск заявок"""
    search_query = message.text.strip()
    
    # Определяем тип поиска
    if search_query.startswith('@'):
        # Поиск по username
        username = search_query[1:]
        user_requests = await get_requests_by_username(username)
        search_type = f"username @{username}"
    else:
        try:
            # Поиск по ID
            user_id = int(search_query)
            user_requests = await get_requests_by_user_id(user_id)
            search_type = f"ID {user_id}"
        except ValueError:
            await message.answer("❌ Неверный формат. Используйте ID (число) или @username")
            return
    
    if not user_requests:
        await message.answer(f"🔍 По запросу '{search_type}' заявки не найдены.")
    else:
        text = f"🔍 <b>Заявки пользователя</b> ({search_type})\n\n"
        
        for request in user_requests[:15]:  # Первые 15 заявок
            request_id, message_text, created_at, status, direction_name = request
            
            created_date = datetime.fromisoformat(created_at).strftime("%d.%m.%Y %H:%M")
            status_emoji = "🔓" if status == 'active' else "🔒"
            short_message = message_text[:40] + "..." if len(message_text) > 40 else message_text
            short_message = escape_html(short_message)
            
            text += f"{status_emoji} <b>#{request_id}</b> ({created_date})\n"
            text += f"📚 {direction_name or 'Без направления'}\n"
            text += f"💬 {short_message}\n\n"
        
        if len(user_requests) > 15:
            text += f"... и еще {len(user_requests) - 15} заявок\n\n"
        
        text += f"💡 Используйте /msg {search_query} для подробной переписки"
        
        await message.answer(text, parse_mode="HTML")
    
    await state.clear()

# Новые обработчики расширенного функционала заявок

@admin_router.callback_query(F.data == "requests_menu")
async def requests_menu_callback(callback: CallbackQuery):
    """Возврат в главное меню заявок"""
    text = (
        "🎫 *Управление заявками*\n\n"
        "Выберите действие:"
    )
    
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_admin_requests_keyboard()
    )
    await callback.answer()

@admin_router.callback_query(F.data.startswith("request_detail:"))
async def show_request_detail(callback: CallbackQuery):
    """Показать детальную информацию о заявке"""
    request_id = int(callback.data.split(":")[1])

    
    # Получаем подробную информацию о заявке
    request_info = await get_request_detailed_info(request_id)
    
    if not request_info:
        await callback.answer("❌ Заявка не найдена", show_alert=True)
        return
    
    request_id, user_id, username, first_name, message_text, created_at, direction_name, status = request_info
    
    # Форматируем дату
    created_date = datetime.fromisoformat(created_at).strftime("%d.%m.%Y %H:%M")
    user_display = f"@{username}" if username else f"ID{user_id}"
    status_emoji = "🔓" if status == "active" else "🔒"
    
    text = f"📝 <b>Заявка #{request_id}</b>\n\n"
    text += f"{status_emoji} <b>Статус:</b> {'Активная' if status == 'active' else 'Закрытая'}\n"
    text += f"👤 <b>Пользователь:</b> {user_display}\n"
    text += f"📅 <b>Создана:</b> {created_date}\n"
    text += f"📚 <b>Направление:</b> {direction_name or 'Без направления'}\n\n"
    text += f"💬 <b>Сообщение:</b>\n{escape_html(message_text)}"
    
    is_active = status == "active"
    keyboard = get_request_detail_keyboard(request_id, user_id, is_active)
    
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()

@admin_router.callback_query(F.data == "requests_by_direction")
async def show_requests_by_direction(callback: CallbackQuery):
    """Показать заявки сгруппированные по направлениям"""
    directions_stats = await get_requests_by_directions()
    
    if not directions_stats:
        text = "📊 <b>Заявки по направлениям</b>\n\n✅ Заявок нет!"
    else:
        text = "📊 <b>Заявки по направлениям</b>\n\n"
        for direction_name, active_count, total_count in directions_stats:
            direction_display = direction_name or "Без направления"
            text += f"📚 <b>{direction_display}</b>\n"
            text += f"   🔓 Активных: {active_count}\n"
            text += f"   📊 Всего: {total_count}\n\n"
    
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="⬅️ К меню заявок", callback_data="requests_menu"))
    
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=builder.as_markup())
    await callback.answer()

@admin_router.callback_query(F.data == "requests_recent")
async def show_recent_requests(callback: CallbackQuery):
    """Показать недавние заявки (за последние 24 часа)"""
    recent_requests = await get_recent_requests()
    
    if not recent_requests:
        text = "⏰ <b>Недавние заявки</b>\n\n✅ За последние 24 часа заявок нет!"
    else:
        text = "⏰ <b>Недавние заявки (24 часа)</b>\n\n"
        builder = InlineKeyboardBuilder()
        
        for request in recent_requests[:10]:
            request_id, user_id, username, first_name, message_text, created_at, direction_name = request
            
            created_date = datetime.fromisoformat(created_at).strftime("%H:%M")
            user_display = f"@{username}" if username else f"ID{user_id}"
            short_message = message_text[:30] + "..." if len(message_text) > 30 else message_text
            
            text += f"📝 <b>#{request_id}</b> ({created_date})\n"
            text += f"👤 {user_display} | 📚 {direction_name or 'Без направления'}\n"
            text += f"💬 {escape_html(short_message)}\n\n"
            
            builder.add(InlineKeyboardButton(
                text=f"📝 #{request_id} - {user_display[:10]}",
                callback_data=f"request_detail:{request_id}"
            ))
    
    builder.add(InlineKeyboardButton(text="⬅️ К меню заявок", callback_data="requests_menu"))
    builder.adjust(1)
    
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=builder.as_markup())
    await callback.answer()



@admin_router.callback_query(F.data.startswith("reply_request:"))
async def reply_request_callback(callback: CallbackQuery, state: FSMContext):
    """Начать процесс ответа на заявку"""
    request_id = int(callback.data.split(":")[1])
    
    # Получаем информацию о заявке
    request_info = await get_request_detailed_info(request_id)
    if not request_info:
        await callback.answer("❌ Заявка не найдена", show_alert=True)
        return
    
    # Сохраняем ID заявки в состояние
    await state.update_data(request_id=request_id)
    await state.set_state(AdminStates.waiting_for_request_answer)
    
    user_display = f"@{request_info[2]}" if request_info[2] else f"ID{request_info[1]}"
    
    await callback.message.answer(
        f"💬 *Ответ на заявку #{request_id}*\n\n"
        f"👤 Пользователь: {user_display}\n"
        f"📝 Заявка: {request_info[4][:100]}{'...' if len(request_info[4]) > 100 else ''}\n\n"
        f"✍️ Напишите ваш ответ:",
        parse_mode="Markdown"
    )
    await callback.answer()

@admin_router.message(StateFilter(AdminStates.waiting_for_request_answer))
async def process_request_answer(message: Message, state: FSMContext):
    """Обработать ответ администратора на заявку"""
    data = await state.get_data()
    request_id = data.get('request_id')
    
    if not request_id:
        await message.answer("❌ Ошибка: ID заявки не найден")
        await state.clear()
        return
    
    # Получаем информацию о заявке
    request_info = await get_request_detailed_info(request_id)
    if not request_info:
        await message.answer("❌ Заявка не найдена")
        await state.clear()
        return
    
    user_id = request_info[1]
    admin_reply = message.text
    admin_id = message.from_user.id
    
    # Отправляем ответ пользователю
    try:
        await message.bot.send_message(
            user_id,
            f"✅ *Ответ на вашу заявку #{request_id}*\n\n"
            f"👤 *Ответил:* Администратор\n"
            f"📋 *Статус:* Заявка закрыта\n\n"
            f"💬 *Ваша заявка:*\n{request_info[4]}\n\n"
            f"📝 *Ответ:*\n{admin_reply}\n\n"
            f"💡 Теперь вы можете создать новую заявку, если это необходимо.",
            parse_mode="Markdown"
        )
        
        # Закрываем заявку в базе данных
        success = await db.close_request(request_id)
        
        if success:
            # Обновляем статус в админских уведомлениях
            await db.update_notification_status(message.bot, request_id, "Закрыта (Администратор)", admin_reply)
            
            # Отправляем уведомления преподавателям о закрытии заявки
            await db.notify_teachers_about_closed_request(message.bot, request_id, "Администратор", admin_reply)
            
            await message.answer(
                f"✅ *Ответ отправлен!*\n\n"
                f"📝 Заявка #{request_id} закрыта\n"
                f"👤 Пользователь уведомлен\n"
                f"👨‍🏫 Преподаватели уведомлены",
                parse_mode="Markdown"
            )
        else:
            await message.answer(
                f"⚠️ *Ответ отправлен, но заявка не закрыта в БД*\n\n"
                f"Обратитесь к техническому администратору",
                parse_mode="Markdown"
            )
            
    except Exception as e:
        await message.answer(
            f"❌ *Ошибка отправки ответа*\n\n"
            f"Пользователь заблокировал бота или удалил аккаунт.\n"
            f"Ошибка: {str(e)}",
            parse_mode="Markdown"
        )
    
    await state.clear()

@admin_router.callback_query(F.data.startswith("close_request:"))
async def close_request_callback(callback: CallbackQuery):
    """Закрыть заявку"""
    request_id = int(callback.data.split(":")[1])
    
    # Закрываем заявку
    success = await db.close_request(request_id)
    
    if success:
        # Обновляем статус в админских уведомлениях (без ответа)
        await db.update_notification_status(callback.bot, request_id, "Закрыта (Администратор)")
        
        # Отправляем уведомления преподавателям о закрытии заявки (без ответа)
        await db.notify_teachers_about_closed_request(callback.bot, request_id, "Администратор", "Заявка закрыта без ответа")
        
        await callback.answer("✅ Заявка закрыта", show_alert=True)
        # Обновляем информацию о заявке
        await show_request_detail(callback)
    else:
        await callback.answer("❌ Ошибка при закрытии заявки", show_alert=True)

# Обработчики настроек

@admin_router.callback_query(F.data == "settings_admins")
async def settings_admins_callback(callback: CallbackQuery):
    """Управление админами из настроек"""
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав для выполнения этой команды.", show_alert=True)
        return
    
    await callback.message.edit_text(
        "👥 *Управление администраторами*\n\n"
        "Выберите действие:",
        parse_mode="Markdown",
        reply_markup=get_admin_management_keyboard()
    )
    await callback.answer()

@admin_router.callback_query(F.data == "settings_teachers")
async def settings_teachers_callback(callback: CallbackQuery):
    """Управление преподавателями из настроек"""
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав для выполнения этой команды.", show_alert=True)
        return
    
    await callback.message.edit_text(
        "👨‍🏫 *Управление преподавателями*\n\n"
        "Здесь вы можете управлять преподавателями и их привязками к направлениям.\n\n"
        "Выберите действие:",
        parse_mode="Markdown",
        reply_markup=get_teacher_management_keyboard()
    )
    await callback.answer()

@admin_router.callback_query(F.data == "settings_notifications")
async def settings_notifications_callback(callback: CallbackQuery):
    """Настройка уведомлений из настроек"""
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав для выполнения этой команды.", show_alert=True)
        return
    
    await callback.message.edit_text(
        "📢 *Настройка уведомлений*\n\n"
        "Здесь вы можете управлять чатами, в которые будут приходить уведомления об обратной связи.\n\n"
        "Выберите действие:",
        parse_mode="Markdown",
        reply_markup=get_notification_settings_keyboard()
    )
    await callback.answer()

@admin_router.callback_query(F.data == "settings_requests")
async def settings_requests_callback(callback: CallbackQuery):
    """Настройки заявок"""
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав для выполнения этой команды.", show_alert=True)
        return
    
    text = (
        "🎫 *Настройки заявок*\n\n"
        "🔧 Раздел находится в разработке.\n\n"
        "Планируемые функции:\n"
        "• Автоматическое закрытие старых заявок\n"
        "• Настройка времени ответа\n"
        "• Шаблоны ответов\n"
        "• Категории заявок"
    )
    
    # Создаем простую кнопку "Назад"
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="⬅️ Назад к настройкам", callback_data="back_to_settings"))
    
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@admin_router.callback_query(F.data == "settings_schedule")
async def settings_schedule_callback(callback: CallbackQuery):
    """Настройки расписания"""
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав для выполнения этой команды.", show_alert=True)
        return
    
    from enhanced_keyboards import get_schedule_settings_keyboard
    
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

@admin_router.callback_query(F.data == "back_to_settings")
async def back_to_settings_callback(callback: CallbackQuery):
    """Возврат к настройкам"""
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав для выполнения этой команды.", show_alert=True)
        return
    
    from chat_handler import ChatBehavior
    chat_type = await ChatBehavior.determine_chat_type(callback.message)
    
    text = (
        "⚙️ *Настройки бота*\n\n"
        "Выберите раздел настроек:"
    )
    
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_settings_keyboard(chat_type)
    )
    await callback.answer()

# Обработчики рабочих часов обратной связи

@admin_router.callback_query(F.data == "settings_working_hours")
async def settings_working_hours_callback(callback: CallbackQuery):
    """Настройки рабочих часов обратной связи"""
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав для выполнения этой команды.", show_alert=True)
        return
    
    text = (
        "🕐 *Рабочие часы обратной связи*\n\n"
        "Здесь вы можете настроить время, когда пользователи могут создавать заявки.\n\n"
        "Выберите день недели для настройки:"
    )
    
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_working_hours_keyboard()
    )
    await callback.answer()

@admin_router.callback_query(F.data == "working_hours_back_to_days")
async def working_hours_back_to_days_callback(callback: CallbackQuery):
    """Возврат к списку дней"""
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав для выполнения этой команды.", show_alert=True)
        return
    
    text = (
        "🕐 *Рабочие часы обратной связи*\n\n"
        "Здесь вы можете настроить время, когда пользователи могут создавать заявки.\n\n"
        "Выберите день недели для настройки:"
    )
    
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_working_hours_keyboard()
    )
    await callback.answer()

@admin_router.callback_query(F.data.startswith("working_hours_day:"))
async def working_hours_day_callback(callback: CallbackQuery):
    """Настройка конкретного дня недели"""
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав для выполнения этой команды.", show_alert=True)
        return
    
    day_num = int(callback.data.split(":")[1])
    days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
    day_name = days[day_num]
    
    # Получаем текущие настройки для этого дня
    working_hours = await db.get_working_hours()
    current_hours = None
    
    for hours in working_hours:
        if hours[0] == day_num:
            current_hours = hours[1:]  # start_time, end_time, is_active
            break
    
    text = f"🕐 *Настройка рабочих часов для {day_name}*\n\n"
    
    if current_hours:
        start_time, end_time, is_active = current_hours
        status = "✅ Включен" if is_active else "❌ Отключен"
        text += f"Текущие настройки:\n🕐 {start_time} - {end_time}\n{status}"
    else:
        text += "Настройки не заданы"
    
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_day_working_hours_keyboard(day_num, day_name, current_hours)
    )
    await callback.answer()

@admin_router.callback_query(F.data.startswith("working_hours_add:"))
async def working_hours_add_callback(callback: CallbackQuery, state: FSMContext):
    """Добавление рабочих часов"""
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав для выполнения этой команды.", show_alert=True)
        return
    
    day_num = int(callback.data.split(":")[1])
    days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
    day_name = days[day_num]
    
    await state.update_data(working_hours_day=day_num, working_hours_day_name=day_name)
    
    text = (
        f"🕐 *Добавление рабочих часов для {day_name}*\n\n"
        "Введите время в формате:\n"
        "**HH:MM-HH:MM**\n\n"
        "Например:\n"
        "• 09:00-18:00\n"
        "• 15:00-20:00\n\n"
        "Для отмены отправьте /cancel"
    )
    
    await callback.message.edit_text(text, parse_mode="Markdown")
    await state.set_state(AdminStates.waiting_for_working_hours_time)
    await callback.answer()

@admin_router.callback_query(F.data.startswith("working_hours_edit:"))
async def working_hours_edit_callback(callback: CallbackQuery, state: FSMContext):
    """Редактирование рабочих часов"""
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав для выполнения этой команды.", show_alert=True)
        return
    
    day_num = int(callback.data.split(":")[1])
    days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
    day_name = days[day_num]
    
    await state.update_data(working_hours_day=day_num, working_hours_day_name=day_name)
    
    text = (
        f"🕐 *Редактирование рабочих часов для {day_name}*\n\n"
        "Введите новое время в формате:\n"
        "**HH:MM-HH:MM**\n\n"
        "Например:\n"
        "• 09:00-18:00\n"
        "• 15:00-20:00\n\n"
        "Для отмены отправьте /cancel"
    )
    
    await callback.message.edit_text(text, parse_mode="Markdown")
    await state.set_state(AdminStates.waiting_for_working_hours_time)
    await callback.answer()

@admin_router.message(StateFilter(AdminStates.waiting_for_working_hours_time))
async def process_working_hours_time(message: Message, state: FSMContext):
    """Обработка введенного времени"""
    if message.text == "/cancel":
        await message.answer("❌ Настройка отменена.")
        await state.clear()
        return
    
    # Парсим время
    try:
        time_range = message.text.strip()
        if "-" not in time_range:
            raise ValueError("Неверный формат")
        
        start_time, end_time = time_range.split("-")
        start_time = start_time.strip()
        end_time = end_time.strip()
        
        # Проверяем формат времени
        from datetime import datetime
        datetime.strptime(start_time, "%H:%M")
        datetime.strptime(end_time, "%H:%M")
        
        # Проверяем логику времени
        if start_time >= end_time:
            raise ValueError("Время начала должно быть меньше времени окончания")
        
    except ValueError as e:
        await message.answer(
            "❌ Неверный формат времени!\n\n"
            "Используйте формат: **HH:MM-HH:MM**\n"
            "Например: 09:00-18:00\n\n"
            "Попробуйте еще раз или отправьте /cancel для отмены",
            parse_mode="Markdown"
        )
        return
    
    # Сохраняем в базу
    data = await state.get_data()
    day_num = data.get('working_hours_day')
    day_name = data.get('working_hours_day_name')
    
    await db.set_working_hours(day_num, start_time, end_time, True)
    
    text = (
        f"✅ *Рабочие часы для {day_name} обновлены!*\n\n"
        f"🕐 Время: {start_time} - {end_time}\n"
        f"✅ Статус: Включен"
    )
    
    # Получаем обновленные настройки для отображения клавиатуры
    working_hours = await db.get_working_hours()
    current_hours = None
    
    for hours in working_hours:
        if hours[0] == day_num:
            current_hours = hours[1:]  # start_time, end_time, is_active
            break
    
    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=get_day_working_hours_keyboard(day_num, day_name, current_hours)
    )
    await state.clear()

@admin_router.callback_query(F.data.startswith("working_hours_toggle:"))
async def working_hours_toggle_callback(callback: CallbackQuery):
    """Включение/отключение рабочих часов"""
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав для выполнения этой команды.", show_alert=True)
        return
    
    day_num = int(callback.data.split(":")[1])
    days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
    day_name = days[day_num]
    
    # Получаем текущие настройки
    working_hours = await db.get_working_hours()
    current_hours = None
    
    for hours in working_hours:
        if hours[0] == day_num:
            current_hours = hours[1:]  # start_time, end_time, is_active
            break
    
    if current_hours:
        start_time, end_time, is_active = current_hours
        new_status = not is_active
        await db.set_working_hours(day_num, start_time, end_time, new_status)
        
        status_text = "✅ Включен" if new_status else "❌ Отключен"
        await callback.answer(f"Статус изменен: {status_text}")
        
        # Обновляем сообщение
        text = f"🕐 *Настройка рабочих часов для {day_name}*\n\n"
        text += f"Текущие настройки:\n🕐 {start_time} - {end_time}\n{status_text}"
        
        # Получаем обновленные настройки
        working_hours = await db.get_working_hours()
        current_hours = None
        
        for hours in working_hours:
            if hours[0] == day_num:
                current_hours = hours[1:]  # start_time, end_time, is_active
                break
        
        await callback.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=get_day_working_hours_keyboard(day_num, day_name, current_hours)
        )
    else:
        await callback.answer("❌ Сначала нужно добавить рабочие часы", show_alert=True)

@admin_router.callback_query(F.data.startswith("working_hours_delete:"))
async def working_hours_delete_callback(callback: CallbackQuery):
    """Удаление рабочих часов"""
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав для выполнения этой команды.", show_alert=True)
        return
    
    day_num = int(callback.data.split(":")[1])
    days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
    day_name = days[day_num]
    
    await db.delete_working_hours(day_num)
    
    await callback.answer(f"✅ Рабочие часы для {day_name} удалены")
    
    text = f"🕐 *Настройка рабочих часов для {day_name}*\n\nНастройки не заданы"
    
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_day_working_hours_keyboard(day_num, day_name, None)
    )

@admin_router.callback_query(F.data == "working_hours_show_all")
async def working_hours_show_all_callback(callback: CallbackQuery):
    """Показать все рабочие часы"""
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав для выполнения этой команды.", show_alert=True)
        return
    
    working_hours = await db.get_working_hours()
    days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
    
    if not working_hours:
        text = "🕐 *Рабочие часы обратной связи*\n\n❌ Рабочие часы не настроены"
    else:
        text = "🕐 *Рабочие часы обратной связи*\n\n"
        for day_num, start_time, end_time, is_active in working_hours:
            day_name = days[day_num]
            status = "✅" if is_active else "❌"
            text += f"{status} **{day_name}:** {start_time} - {end_time}\n"
    
    # Создаем кнопку "Назад"
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="⬅️ Назад к дням", callback_data="working_hours_back_to_days"))
    
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

# Статистика

# Обработчик stats_general перенесён в group_handlers.py для избежания конфликтов

# Обработчик stats_requests перенесён в group_handlers.py для избежания конфликтов

# Обработчик stats_users перенесён в group_handlers.py для избежания конфликтов

# Обработчик stats_directions перенесён в group_handlers.py для избежания конфликтов

# Дополнительные админские команды

@admin_router.message(Command("broadcast"))
@require_permission("admin_management")
async def start_broadcast(message: Message, state: FSMContext, **kwargs):
    """Рассылка сообщения всем пользователям"""
    if not await db.is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для выполнения этой команды.")
        return
    
    await message.answer(
        "📢 *Рассылка сообщения*\n\n"
        "Отправьте текст сообщения, которое будет разослано всем пользователям бота.\n\n"
        "⚠️ *Внимание:* Рассылка будет отправлена всем пользователям, которые когда-либо писали боту!\n\n"
        "Для отмены отправьте /cancel",
        parse_mode="Markdown"
    )
    await state.set_state(AdminStates.waiting_for_broadcast_message)

@admin_router.message(StateFilter(AdminStates.waiting_for_broadcast_message))
async def process_broadcast(message: Message, state: FSMContext):
    """Обработать рассылку"""
    if message.text == "/cancel":
        await message.answer("❌ Рассылка отменена.")
        await state.clear()
        return
    
    broadcast_text = message.text
    
    # Получаем всех пользователей
    users = await get_all_bot_users()
    
    if not users:
        await message.answer("❌ Пользователи для рассылки не найдены.")
        await state.clear()
        return
    
    # Подтверждение рассылки
    confirm_text = (
        f"📢 *Подтверждение рассылки*\n\n"
        f"👥 *Получателей:* {len(users)}\n\n"
        f"📝 *Текст сообщения:*\n{broadcast_text}\n\n"
        f"❓ Отправить рассылку?"
    )
    
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="✅ Отправить", callback_data="confirm_broadcast"))
    builder.add(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_broadcast"))
    builder.adjust(2)
    
    await message.answer(confirm_text, parse_mode="Markdown", reply_markup=builder.as_markup())
    await state.update_data(broadcast_text=broadcast_text, users=users)

@admin_router.callback_query(F.data == "confirm_broadcast")
async def confirm_broadcast(callback: CallbackQuery, state: FSMContext):
    """Подтвердить рассылку"""
    data = await state.get_data()
    broadcast_text = data.get('broadcast_text')
    users = data.get('users', [])
    
    await callback.message.edit_text("📤 Начинаю рассылку...")
    
    success_count = 0
    error_count = 0
    
    for user_id in users:
        try:
            await callback.bot.send_message(
                user_id,
                f"📢 *Сообщение от администрации IT-Cube*\n\n{broadcast_text}",
                parse_mode="Markdown"
            )
            success_count += 1
            await asyncio.sleep(0.05)  # Небольшая задержка для избежания лимитов
        except Exception:
            error_count += 1
    
    result_text = (
        f"📊 *Результат рассылки*\n\n"
        f"✅ *Успешно отправлено:* {success_count}\n"
        f"❌ *Ошибок:* {error_count}\n"
        f"👥 *Всего пользователей:* {len(users)}"
    )
    
    await callback.message.edit_text(result_text, parse_mode="Markdown")
    await state.clear()

@admin_router.callback_query(F.data == "cancel_broadcast")
async def cancel_broadcast(callback: CallbackQuery, state: FSMContext):
    """Отменить рассылку"""
    await callback.message.edit_text("❌ Рассылка отменена.")
    await state.clear()

# Вспомогательные функции

def escape_markdown(text: str) -> str:
    """Экранировать специальные символы markdown"""
    if not text:
        return ""
    
    # Экранируем только критичные markdown символы, которые могут нарушить разметку
    # Убираем точки и другие символы, которые редко вызывают проблемы
    escape_chars = ['*', '_', '[', ']', '`', '~', '>', '#', '+', '-', '=', '|', '{', '}', '!', '\\']
    for char in escape_chars:
        text = text.replace(char, f'\\{char}')
    
    return text

def escape_html(text: str) -> str:
    """Экранировать HTML символы"""
    if not text:
        return ""
    
    # Экранируем HTML символы для безопасности
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    text = text.replace('"', '&quot;')
    text = text.replace("'", '&#x27;')
    
    return text

async def get_active_requests_detailed():
    """Получить детальную информацию об активных заявках"""
    try:
        async with aiosqlite.connect(db.db_path) as conn:
            cursor = await conn.execute('''
                SELECT fm.id, fm.user_id, fm.username, fm.first_name, 
                       fm.message_text, fm.created_at, d.name as direction_name
                FROM feedback_messages fm
                LEFT JOIN directions d ON fm.direction_id = d.id
                WHERE fm.status = 'active'
                ORDER BY fm.created_at DESC
            ''')
            return await cursor.fetchall()
    except Exception:
        return []

async def get_closed_requests_summary():
    """Получить сводку закрытых заявок"""
    try:
        async with aiosqlite.connect(db.db_path) as conn:
            cursor = await conn.execute('''
                SELECT COUNT(*) as total,
                       COUNT(CASE WHEN answered_at > datetime('now', '-1 day') THEN 1 END) as today,
                       COUNT(CASE WHEN answered_at > datetime('now', '-7 days') THEN 1 END) as week
                FROM feedback_messages 
                WHERE status = 'closed'
            ''')
            stats = await cursor.fetchone()
            
            if not stats:
                return "📊 Закрытых заявок нет"
            
            total, today, week = stats
            
            text = f"📊 Всего закрыто: {total}\n"
            text += f"📅 За сегодня: {today}\n"
            text += f"📅 За неделю: {week}"
            
            return text
            
    except Exception as e:
        return f"❌ Ошибка получения данных: {str(e)}"

async def get_requests_by_username(username: str):
    """Получить заявки по username"""
    try:
        async with aiosqlite.connect(db.db_path) as conn:
            cursor = await conn.execute('''
                SELECT fm.id, fm.message_text, fm.created_at, fm.status, d.name as direction_name
                FROM feedback_messages fm
                LEFT JOIN directions d ON fm.direction_id = d.id
                WHERE fm.username = ?
                ORDER BY fm.created_at DESC
            ''', (username,))
            return await cursor.fetchall()
    except Exception:
        return []

async def get_requests_by_user_id(user_id: int):
    """Получить заявки по user_id"""
    try:
        async with aiosqlite.connect(db.db_path) as conn:
            cursor = await conn.execute('''
                SELECT fm.id, fm.message_text, fm.created_at, fm.status, d.name as direction_name
                FROM feedback_messages fm
                LEFT JOIN directions d ON fm.direction_id = d.id
                WHERE fm.user_id = ?
                ORDER BY fm.created_at DESC
            ''', (user_id,))
            return await cursor.fetchall()
    except Exception:
        return []

async def get_general_statistics():
    """Получить общую статистику"""
    try:
        async with aiosqlite.connect(db.db_path) as conn:
            # Статистика заявок
            cursor = await conn.execute('''
                SELECT 
                    COUNT(*) as total_requests,
                    COUNT(CASE WHEN status = 'active' THEN 1 END) as active_requests,
                    COUNT(CASE WHEN created_at > datetime('now', '-1 day') THEN 1 END) as today_requests,
                    COUNT(CASE WHEN created_at > datetime('now', '-7 days') THEN 1 END) as week_requests
                FROM feedback_messages
            ''')
            request_stats = await cursor.fetchone()
            
            # Статистика пользователей
            cursor = await conn.execute('''
                SELECT 
                    COUNT(DISTINCT user_id) as total_users,
                    COUNT(DISTINCT CASE WHEN created_at > datetime('now', '-30 days') THEN user_id END) as active_users
                FROM feedback_messages
            ''')
            user_stats = await cursor.fetchone()
            
            # Статистика админов и преподавателей
            cursor = await conn.execute('SELECT COUNT(*) FROM admins')
            admin_count = (await cursor.fetchone())[0]
            
            cursor = await conn.execute('SELECT COUNT(*) FROM teachers WHERE is_active = TRUE')
            teacher_count = (await cursor.fetchone())[0]
            
            if not request_stats:
                return "❌ Не удалось получить статистику"
            
            total_req, active_req, today_req, week_req = request_stats
            total_users, active_users = user_stats if user_stats else (0, 0)
            
            text = "📊 *Общая статистика IT-Cube Bot*\n\n"
            
            text += "🎫 *Заявки:*\n"
            text += f"• Всего: {total_req}\n"
            text += f"• Активных: {active_req}\n"
            text += f"• За сегодня: {today_req}\n"
            text += f"• За неделю: {week_req}\n\n"
            
            text += "👥 *Пользователи:*\n"
            text += f"• Всего: {total_users}\n"
            text += f"• Активных за месяц: {active_users}\n\n"
            
            text += "👑 *Персонал:*\n"
            text += f"• Администраторов: {admin_count}\n"
            text += f"• Преподавателей: {teacher_count}\n\n"
            
            if total_req > 0:
                response_rate = round(((total_req - active_req) / total_req) * 100, 1)
                text += f"📈 *Процент обработки заявок:* {response_rate}%"
            
            return text
            
    except Exception as e:
        # Экранируем специальные символы Markdown в сообщении об ошибке
        error_msg = escape_markdown(str(e))
        return f"❌ Ошибка получения статистики: {error_msg}"

async def get_requests_statistics():
    """Статистика заявок"""
    # Здесь будет детальная статистика заявок
    return "🎫 *Подробная статистика заявок будет добавлена*"

async def get_users_statistics():
    """Статистика пользователей"""
    # Здесь будет статистика пользователей
    return "👥 *Подробная статистика пользователей будет добавлена*"

async def get_directions_statistics():
    """Статистика по направлениям"""
    try:
        async with aiosqlite.connect(db.db_path) as conn:
            cursor = await conn.execute('''
                SELECT d.name, COUNT(fm.id) as request_count,
                       COUNT(CASE WHEN fm.status = 'active' THEN 1 END) as active_count
                FROM directions d
                LEFT JOIN feedback_messages fm ON d.id = fm.direction_id
                GROUP BY d.id, d.name
                ORDER BY request_count DESC
            ''')
            direction_stats = await cursor.fetchall()
            
            if not direction_stats:
                return "📚 *Статистика по направлениям*\n\n❌ Данные не найдены"
            
            text = "📚 *Статистика по направлениям*\n\n"
            
            for direction_name, total, active in direction_stats:
                text += f"📖 *{direction_name}*\n"
                text += f"• Всего заявок: {total}\n"
                text += f"• Активных: {active}\n\n"
            
            return text
            
    except Exception as e:
        # Экранируем специальные символы Markdown в сообщении об ошибке
        error_msg = escape_markdown(str(e))
        return f"❌ Ошибка получения статистики: {error_msg}"

async def get_all_bot_users():
    """Получить всех пользователей бота"""
    try:
        async with aiosqlite.connect(db.db_path) as conn:
            cursor = await conn.execute('SELECT DISTINCT user_id FROM feedback_messages')
            users = await cursor.fetchall()
            return [user[0] for user in users]
    except Exception:
        return []

# Новые вспомогательные функции для расширенного функционала заявок

async def get_request_detailed_info(request_id: int):
    """Получить подробную информацию о конкретной заявке"""
    try:
        async with aiosqlite.connect(db.db_path) as conn:
            cursor = await conn.execute('''
                SELECT fm.id, fm.user_id, fm.username, fm.first_name, fm.message_text, 
                       fm.created_at, d.name as direction_name, fm.status
                FROM feedback_messages fm
                LEFT JOIN directions d ON fm.direction_id = d.id
                WHERE fm.id = ?
            ''', (request_id,))
            result = await cursor.fetchone()
            return result
    except Exception as e:
        return None

async def get_requests_by_directions():
    """Получить статистику заявок по направлениям"""
    try:
        async with aiosqlite.connect(db.db_path) as conn:
            cursor = await conn.execute('''
                SELECT 
                    COALESCE(d.name, 'Без направления') as direction_name,
                    COUNT(CASE WHEN fm.status = 'active' THEN 1 END) as active_count,
                    COUNT(*) as total_count
                FROM feedback_messages fm
                LEFT JOIN directions d ON fm.direction_id = d.id
                GROUP BY d.name
                ORDER BY total_count DESC
            ''')
            return await cursor.fetchall()
    except Exception:
        return []

async def get_recent_requests():
    """Получить недавние заявки (за последние 24 часа)"""
    try:
        async with aiosqlite.connect(db.db_path) as conn:
            cursor = await conn.execute('''
                SELECT fm.id, fm.user_id, fm.username, fm.first_name, fm.message_text, 
                       fm.created_at, d.name as direction_name
                FROM feedback_messages fm
                LEFT JOIN directions d ON fm.direction_id = d.id
                WHERE fm.created_at > datetime('now', '-1 day')
                ORDER BY fm.created_at DESC
            ''')
            return await cursor.fetchall()
    except Exception:
        return []


