import re
from aiogram import Router, F
from aiogram.filters import Command, StateFilter, ChatMemberUpdatedFilter, IS_MEMBER, IS_NOT_MEMBER
from aiogram.types import Message, CallbackQuery, ChatMemberUpdated
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import db
from keyboards import (
    get_main_keyboard, get_schedule_directions_keyboard,
    get_direction_days_keyboard, get_back_to_directions_keyboard,
    get_admin_management_keyboard, get_cancel_keyboard, get_cancel_inline_keyboard,
    get_notification_settings_keyboard, get_back_to_notification_settings_keyboard,
    get_notification_chat_actions_keyboard, get_directions_keyboard,
    get_teacher_management_keyboard, get_back_to_teacher_management_keyboard,
    get_directions_list_keyboard, get_direction_teachers_keyboard, get_send_feedback_keyboard
)
from schedule_parser import schedule_parser
from chat_handler import ChatType, ChatBehavior
from enhanced_keyboards import get_keyboard_for_chat_type, get_admin_keyboard, get_teacher_keyboard

router = Router()

# Вспомогательная функция для безопасного редактирования сообщений
async def safe_edit_message(message, text, **kwargs):
    """
    Безопасно редактирует сообщение, если не получается - отправляет новое
    """
    try:
        await message.edit_text(text, **kwargs)
        return True
    except Exception as e:
        print(f"Ошибка редактирования сообщения: {e}")
        try:
            await message.answer(text, **kwargs)
            return False
        except Exception as e2:
            print(f"Ошибка отправки нового сообщения: {e2}")
            return False

# Состояния для FSM
class AdminStates(StatesGroup):
    waiting_for_admin_id = State()
    waiting_for_remove_admin_id = State()

class FeedbackStates(StatesGroup):
    waiting_for_direction = State()
    waiting_for_message = State()
    waiting_for_attachments = State()

class NotificationStates(StatesGroup):
    waiting_for_chat_id = State()

class TeacherStates(StatesGroup):
    waiting_for_teacher_id = State()
    waiting_for_remove_teacher_id = State()
    waiting_for_teacher_assignment = State()

# Обработка добавления бота в чат/группу
@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=IS_NOT_MEMBER >> IS_MEMBER))
async def bot_added_to_chat(chat_member: ChatMemberUpdated):
    """Обработка события добавления бота в чат или группу"""
    chat = chat_member.chat
    
    # Проверяем, что это не личный чат
    if chat.type == 'private':
        return
    
    # Формируем сообщение с информацией о чате
    chat_title = chat.title or "Без названия"
    chat_type_ru = {
        'group': 'Группа',
        'supergroup': 'Супергруппа', 
        'channel': 'Канал'
    }.get(chat.type, chat.type)
    
    welcome_text = (
        f"👋 Привет! Я добавлен в {chat_type_ru.lower()}!\n\n"
        f"📋 *Название:* {chat_title}\n"
        f"🆔 *ID чата:* `{chat.id}`\n"
        f"📱 *Тип:* {chat_type_ru}\n\n"
        f"🤖 Я бот IT-Cube для работы с расписанием и обратной связью.\n\n"
        f"📢 *Для админов:* Вы можете добавить этот чат в список для получения уведомлений об обратной связи.\n"
        f"Скопируйте ID чата: `{chat.id}` и используйте в админ-панели.\n\n"
        f"💡 *Команды:*\n"
        f"• `/chatid` - показать ID этого чата\n"
        f"• `/start` - показать главное меню\n"
        f"• `/menu` - показать главное меню"
    )
    
    try:
        await chat_member.bot.send_message(
            chat.id, 
            welcome_text, 
            parse_mode="Markdown"
        )
    except Exception:
        # Бот может не иметь прав на отправку сообщений
        pass

# Команда для получения ID текущего чата
@router.message(Command("chatid"))
async def show_chat_id(message: Message):
    """Показать ID текущего чата"""
    chat = message.chat
    
    # Поддержка топиков (форумов)
    message_thread_id = getattr(message, 'message_thread_id', None)
    
    if chat.type == 'private':
        text = (
            f"💬 *Личный чат*\n\n"
            f"🆔 *Ваш ID:* `{message.from_user.id}`\n"
            f"🆔 *ID чата:* `{chat.id}`\n\n"
            f"💡 Это ваш личный чат с ботом."
        )
    else:
        chat_title = chat.title or "Без названия"
        chat_type_ru = {
            'group': 'Группа',
            'supergroup': 'Супергруппа',
            'channel': 'Канал'
        }.get(chat.type, chat.type)
        
        topic_info = ""
        if message_thread_id:
            topic_info = f"📍 *ID топика:* `{message_thread_id}`\n"
        
        text = (
            f"📋 *{chat_type_ru}: {chat_title}*\n\n"
            f"🆔 *ID чата:* `{chat.id}`\n"
            f"{topic_info}"
            f"📱 *Тип:* {chat_type_ru}\n\n"
            f"📢 *Для добавления в уведомления:*\n"
            f"Скопируйте ID: `{chat.id}`\n"
            f"И используйте в админ-панели бота."
        )
    
    # message.reply() автоматически использует message_thread_id из исходного сообщения
    await message.reply(text, parse_mode="Markdown")

# Обработка команды /start в группах (покажет ID)
@router.message(Command("start"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_start_in_group(message: Message):
    """Обработка команды /start в группах - показываем ID чата"""
    chat = message.chat
    chat_title = chat.title or "Без названия"
    chat_type_ru = {
        'group': 'Группа',
        'supergroup': 'Супергруппа'
    }.get(chat.type, chat.type)
    
    # Поддержка топиков (форумов)
    message_thread_id = getattr(message, 'message_thread_id', None)
    topic_info = ""
    if message_thread_id:
        topic_info = f"📍 *Топик ID:* `{message_thread_id}`\n"
    
    text = (
        f"👋 Привет! Я бот IT-Cube!\n\n"
        f"📋 *{chat_type_ru}: {chat_title}*\n"
        f"🆔 *ID чата:* `{chat.id}`\n"
        f"{topic_info}"
        f"🤖 Основные функции:\n"
        f"• 📅 Просмотр расписания IT-Cube\n"
        f"• 💬 Обратная связь с администрацией\n"
        f"• 📢 Получение уведомлений (для админов)\n\n"
        f"💡 *Полезные команды:*\n"
        f"• `/chatid` - показать ID этого чата\n"
        f"• `/start` - показать главное меню\n"
        f"• `/menu` - показать главное меню\n\n"
        f"📢 *Для админов:* Скопируйте ID `{chat.id}` чтобы добавить этот чат в настройки уведомлений."
    )
    
    # message.reply() автоматически использует message_thread_id из исходного сообщения
    await message.reply(text, parse_mode="Markdown")

# Команда /start (в личных сообщениях)
@router.message(Command("start"), F.chat.type == "private")
async def cmd_start_private(message: Message):
    # Определяем тип чата и роль пользователя
    chat_type = await ChatBehavior.determine_chat_type(message)
    
    # Обновляем информацию о пользователе если он админ или преподаватель
    if chat_type in [ChatType.PRIVATE_ADMIN, ChatType.PRIVATE_TEACHER]:
        await db.update_admin_info(
            message.from_user.id,
            message.from_user.username,
            message.from_user.first_name
        )
    
    # Получаем приветственное сообщение для типа чата
    welcome_text = ChatBehavior.get_welcome_message(
        chat_type,
        message.from_user.first_name
    )
    
    # Получаем соответствующую клавиатуру
    keyboard = get_keyboard_for_chat_type(chat_type, message.from_user.id, None)
    
    await message.answer(welcome_text, parse_mode="Markdown", reply_markup=keyboard)

    # Команда /menu (в личных сообщениях)
@router.message(Command("menu"), F.chat.type == "private")
async def cmd_menu_private(message: Message):
    # Определяем тип чата и роль пользователя
    chat_type = await ChatBehavior.determine_chat_type(message)
    
    # Обновляем информацию о пользователе если он админ или преподаватель
    if chat_type in [ChatType.PRIVATE_ADMIN, ChatType.PRIVATE_TEACHER]:
        await db.update_admin_info(
            message.from_user.id,
            message.from_user.username,
            message.from_user.first_name
        )
    
    # Получаем приветственное сообщение для типа чата
    welcome_text = ChatBehavior.get_welcome_message(
        chat_type,
        message.from_user.first_name
    )
    
    # Получаем соответствующую клавиатуру
    keyboard = get_keyboard_for_chat_type(chat_type, message.from_user.id, None)
    
    await message.answer(welcome_text, parse_mode="Markdown", reply_markup=keyboard)

# Расписание
@router.message(F.text == "📅 Расписание")
async def show_schedule_menu(message: Message):
    await message.answer(
        "📅 *Выберите направление для просмотра расписания:*",
        parse_mode="Markdown",
        reply_markup=get_schedule_directions_keyboard()
    )

# Обработка выбора направления
@router.callback_query(F.data.startswith("dir:"))
async def show_direction_schedule(callback: CallbackQuery):
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

# Полное расписание направления
@router.callback_query(F.data.startswith("full:"))
async def show_full_schedule(callback: CallbackQuery):
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
        reply_markup=get_back_to_directions_keyboard()
    )
    await callback.answer()

# Расписание на день
@router.callback_query(F.data.startswith("day:"))
async def show_day_schedule(callback: CallbackQuery):
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
        reply_markup=get_back_to_directions_keyboard()
    )
    await callback.answer()

# Назад к направлениям
@router.callback_query(F.data == "back_to_directions")
async def back_to_directions(callback: CallbackQuery):
    await callback.message.edit_text(
        "📅 *Выберите направление для просмотра расписания:*",
        parse_mode="Markdown",
        reply_markup=get_schedule_directions_keyboard()
    )
    await callback.answer()

# Обратная связь
@router.message(F.text == "💬 Обратная связь")
async def feedback_menu(message: Message, state: FSMContext):
    # Проверяем рабочие часы обратной связи
    is_available, error_message = await db.is_feedback_available_now()
    
    if not is_available:
        # Получаем все рабочие часы для отображения
        working_hours = await db.get_working_hours()
        days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        
        if working_hours:
            hours_text = "🕐 *Рабочие часы обратной связи:*\n\n"
            for day_num, start_time, end_time, is_active in working_hours:
                if is_active:
                    day_name = days[day_num]
                    hours_text += f"• {day_name}: {start_time} - {end_time}\n"
        else:
            hours_text = "🕐 Рабочие часы не настроены"
        
        await message.answer(
            f"❌ *Обратная связь недоступна*\n\n"
            f"⏰ {error_message}\n\n"
            f"{hours_text}\n\n"
            f"💡 Пожалуйста, обратитесь в рабочее время.",
            parse_mode="Markdown"
        )
        return
    
    # Проверяем, есть ли у пользователя активная заявка
    has_active = await db.has_active_request(message.from_user.id)
    
    if has_active:
        # Получаем информацию об активной заявке
        active_request = await db.get_active_request(message.from_user.id)
        if active_request:
            request_id, request_text, created_at = active_request
            # Форматируем дату
            from datetime import datetime
            created_date = datetime.fromisoformat(created_at).strftime("%d.%m.%Y %H:%M")
            
            await message.answer(
                "⚠️ *У вас есть активная заявка на рассмотрении*\n\n"
                f"📝 *Заявка #{request_id}*\n"
                f"📅 *Создана:* {created_date}\n\n"
                f"💬 *Текст заявки:*\n{request_text}\n\n"
                "❌ Вы не можете создать новую заявку, пока текущая активна.\n"
                "⏳ Пожалуйста, дождитесь ответа от администрации.\n\n"
                "💡 После получения ответа вы сможете создать новую заявку.",
                parse_mode="Markdown"
            )
            return
    
    # Получаем список направлений
    directions = await db.get_all_directions()
    
    if not directions:
        await message.answer(
            "❌ *Направления не найдены*\n\n"
            "В данный момент нет доступных направлений для создания заявки.\n"
            "Обратитесь к администратору.",
            parse_mode="Markdown"
        )
        return
    
    # Создаем клавиатуру с направлениями
    from keyboards import get_directions_keyboard
    
    await message.answer(
        "💬 *Создание заявки*\n\n"
        "📚 *Шаг 1:* Выберите получателя вашей заявки:\n\n"
        "👑 *Администрация* - для общих вопросов, жалоб и предложений\n"
        "📚 *Направления* - для вопросов по конкретным предметам\n\n"
        "💡 Заявки по направлениям отправляются преподавателям и администрации,\n"
        "заявки для администрации - только администрации.",
        parse_mode="Markdown",
        reply_markup=get_directions_keyboard(directions)
    )
    await state.set_state(FeedbackStates.waiting_for_direction)

# Обработка выбора направления для заявки
@router.callback_query(F.data.startswith("select_direction:"))
async def select_direction_for_feedback(callback: CallbackQuery, state: FSMContext):
    direction_value = callback.data.split(":", 1)[1]
    
    # Проверяем, выбрана ли администрация
    if direction_value == "admin":
        # Сохраняем специальное значение для администрации
        await state.update_data(direction_id="admin")
        direction_name = "Администрация"
        
        await callback.message.edit_text(
            f"💬 *Создание заявки*\n\n"
            f"👑 *Выбрано:* {direction_name}\n\n"
            f"✍️ *Шаг 2:* Опишите ваш вопрос или проблему:\n\n"
            f"📝 *Например:*\n"
            f"• Административные вопросы\n"
            f"• Жалобы или предложения\n"
            f"• Общие вопросы по обучению\n"
            f"• Техническая поддержка\n\n"
            f"💌 Напишите текст заявки следующим сообщением.\n"
            f"📎 Вы также можете прикрепить фото, документы или другие файлы.",
            parse_mode="Markdown",
            reply_markup=get_cancel_inline_keyboard()
        )
    else:
        # Обычное направление
        direction_id = int(direction_value)
        
        # Сохраняем выбранное направление в состоянии
        await state.update_data(direction_id=direction_id)
        
        # Получаем информацию о направлении
        direction = await db.get_direction_by_id(direction_id)
        if not direction:
            await callback.answer("❌ Направление не найдено", show_alert=True)
            return
        
        direction_name = direction[1]
        
        await callback.message.edit_text(
            f"💬 *Создание заявки*\n\n"
            f"📚 *Выбранное направление:* {direction_name}\n\n"
            f"✍️ *Шаг 2:* Опишите ваш вопрос или проблему:\n\n"
            f"📝 *Например:*\n"
            f"• Вопрос по материалу урока\n"
            f"• Техническая проблема\n"
            f"• Запрос на консультацию\n"
            f"• Предложение по улучшению\n\n"
            f"💌 Напишите текст заявки следующим сообщением.\n"
            f"📎 Вы также можете прикрепить фото, документы или другие файлы.",
            parse_mode="Markdown",
            reply_markup=get_cancel_inline_keyboard()
        )
    
    await state.set_state(FeedbackStates.waiting_for_message)
    await callback.answer()

# Обработка отмены создания заявки
@router.callback_query(F.data == "cancel_feedback")
async def cancel_feedback(callback: CallbackQuery, state: FSMContext):
    # Получаем данные из состояния для удаления сообщения со статусом
    data = await state.get_data()
    last_message_id = data.get('last_attachment_message_id')
    
    # Удаляем сообщение со статусом прикреплений (если есть)
    if last_message_id:
        try:
            await callback.bot.delete_message(callback.message.chat.id, last_message_id)
        except:
            pass  # Игнорируем ошибки удаления
    
    is_admin = await db.is_admin(callback.from_user.id)
    is_teacher = await db.is_teacher(callback.from_user.id)
    
    if is_admin:
        keyboard = get_admin_keyboard()
    elif is_teacher:
        keyboard = get_teacher_keyboard()
    else:
        keyboard = get_main_keyboard()
    
    await callback.message.edit_text("❌ Создание заявки отменено.")
    await state.clear()
    await callback.answer()
    
    # Отправляем новое сообщение с правильной клавиатурой
    await callback.message.answer("Используйте кнопки меню для навигации.", reply_markup=keyboard)

# Получение текста заявки
@router.message(StateFilter(FeedbackStates.waiting_for_message))
async def receive_feedback_text(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        is_admin = await db.is_admin(message.from_user.id)
        is_teacher = await db.is_teacher(message.from_user.id)
        
        if is_admin:
            keyboard = get_admin_keyboard()
        elif is_teacher:
            keyboard = get_teacher_keyboard()
        else:
            keyboard = get_main_keyboard()
        
        await message.answer("Отменено.", reply_markup=keyboard)
        await state.clear()
        return
    
    # Дополнительная проверка на активную заявку (защита от спама)
    has_active = await db.has_active_request(message.from_user.id)
    if has_active:
        # Определяем правильную клавиатуру
        is_admin = await db.is_admin(message.from_user.id)
        is_teacher = await db.is_teacher(message.from_user.id)
        
        if is_admin:
            active_keyboard = get_admin_keyboard()
        elif is_teacher:
            active_keyboard = get_teacher_keyboard()
        else:
            active_keyboard = get_main_keyboard()
        
        await message.answer(
            "⚠️ У вас уже есть активная заявка на рассмотрении.\n"
            "Пожалуйста, дождитесь ответа администрации.",
            reply_markup=active_keyboard
        )
        await state.clear()
        return
    
    # Проверяем, что это текстовое сообщение
    if not message.text:
        await message.answer(
            "❌ Пожалуйста, напишите текст заявки.\n"
            "Файлы можно будет прикрепить на следующем шаге.",
            reply_markup=get_cancel_inline_keyboard()
        )
        return
    
    # Получаем данные из состояния
    data = await state.get_data()
    direction_id = data.get('direction_id')
    
    if not direction_id:
        # Определяем правильную клавиатуру
        is_admin = await db.is_admin(message.from_user.id)
        is_teacher = await db.is_teacher(message.from_user.id)
        
        if is_admin:
            error_keyboard = get_admin_keyboard()
        elif is_teacher:
            error_keyboard = get_teacher_keyboard()
        else:
            error_keyboard = get_main_keyboard()
        
        await message.answer(
            "❌ Ошибка: направление не выбрано. Попробуйте еще раз.",
            reply_markup=error_keyboard
        )
        await state.clear()
        return
    
    # Сохраняем текст заявки в состоянии
    await state.update_data(feedback_text=message.text)
    
    # Переходим к этапу прикрепления файлов
    direction_name = "Администрация" if direction_id == "admin" else (await db.get_direction_by_id(direction_id))[1]
    
    await message.answer(
        f"💬 *Создание заявки*\n\n"
        f"📚 *Направление:* {direction_name}\n"
        f"✅ *Текст заявки получен*\n\n"
        f"📎 *Шаг 3 (необязательно):* Прикрепите файлы\n\n"
        f"Вы можете прикрепить:\n"
        f"• 📷 Фотографии\n"
        f"• 📄 Документы (PDF, DOC, TXT и др.)\n"
        f"• 🎵 Аудиофайлы\n"
        f"• 🎬 Видеофайлы\n\n"
        f"📤 Отправьте файлы или нажмите *\"Отправить заявку\"* если файлы не нужны.",
        parse_mode="Markdown",
        reply_markup=get_send_feedback_keyboard()
    )
    
    await state.set_state(FeedbackStates.waiting_for_attachments)

# Обработчики прикреплений к заявке
@router.message(StateFilter(FeedbackStates.waiting_for_attachments))
async def handle_attachments(message: Message, state: FSMContext):
    # Получаем данные из состояния
    data = await state.get_data()
    attachments = data.get('attachments', [])
    
    # Обрабатываем разные типы медиа
    file_info = None
    file_type = None
    file_name = None
    file_size = None
    mime_type = None
    
    if message.photo:
        # Фото - берем самое большое разрешение
        photo = message.photo[-1]
        file_info = photo
        file_type = "photo"
        file_size = photo.file_size
        mime_type = "image/jpeg"
        file_name = f"photo_{photo.file_id[:8]}.jpg"
        
    elif message.document:
        file_info = message.document
        file_type = "document"
        file_name = message.document.file_name or f"document_{message.document.file_id[:8]}"
        file_size = message.document.file_size
        mime_type = message.document.mime_type
        
    elif message.video:
        file_info = message.video
        file_type = "video"
        file_name = f"video_{message.video.file_id[:8]}.mp4"
        file_size = message.video.file_size
        mime_type = message.video.mime_type or "video/mp4"
        
    elif message.audio:
        file_info = message.audio
        file_type = "audio"
        file_name = message.audio.file_name or f"audio_{message.audio.file_id[:8]}.mp3"
        file_size = message.audio.file_size
        mime_type = message.audio.mime_type or "audio/mpeg"
        
    elif message.voice:
        file_info = message.voice
        file_type = "voice"
        file_name = f"voice_{message.voice.file_id[:8]}.ogg"
        file_size = message.voice.file_size
        mime_type = message.voice.mime_type or "audio/ogg"
        
    elif message.video_note:
        file_info = message.video_note
        file_type = "video_note"
        file_name = f"video_note_{message.video_note.file_id[:8]}.mp4"
        file_size = message.video_note.file_size
        mime_type = "video/mp4"
        
    else:
        await message.answer(
            "❌ Неподдерживаемый тип файла.\n"
            "Поддерживаются: фото, документы, видео, аудио, голосовые сообщения.",
            reply_markup=get_send_feedback_keyboard()
        )
        return
    
    # Добавляем файл к списку прикреплений
    attachment = {
        'file_id': file_info.file_id,
        'file_type': file_type,
        'file_name': file_name,
        'file_size': file_size,
        'mime_type': mime_type
    }
    attachments.append(attachment)
    
    # Обновляем состояние
    await state.update_data(attachments=attachments)
    
    # Удаляем предыдущее сообщение со статусом (если есть)
    last_message_id = data.get('last_attachment_message_id')
    if last_message_id:
        try:
            await message.bot.delete_message(message.chat.id, last_message_id)
        except:
            pass  # Игнорируем ошибки удаления
    
    # Создаем новое сообщение со статусом
    status_message = await message.answer(
        f"📎 *Прикрепленные файлы:* {len(attachments)} файл(ов)\n\n"
        f"📋 *Список файлов:*\n",
        parse_mode="Markdown",
        reply_markup=get_send_feedback_keyboard()
    )
    
    # Добавляем список файлов
    file_list = ""
    for i, att in enumerate(attachments, 1):
        safe_name = escape_markdown(att['file_name'])
        size_mb = (att['file_size'] / (1024 * 1024)) if att['file_size'] else 0
        file_list += f"{i}. `{safe_name}` ({size_mb:.2f} МБ)\n"
    
    # Обновляем сообщение с полным списком
    await status_message.edit_text(
        f"📎 *Прикрепленные файлы:* {len(attachments)} файл(ов)\n\n"
        f"📋 *Список файлов:*\n{file_list}\n"
        f"📤 Можете прикрепить еще файлы или отправить заявку.",
        parse_mode="Markdown",
        reply_markup=get_send_feedback_keyboard()
    )
    
    # Сохраняем ID нового сообщения
    await state.update_data(last_attachment_message_id=status_message.message_id)

# Обработчик кнопки "Отправить заявку"
@router.callback_query(F.data == "send_feedback")
async def send_feedback_with_attachments(callback: CallbackQuery, state: FSMContext):
    # Получаем все данные из состояния
    data = await state.get_data()
    direction_id = data.get('direction_id')
    feedback_text = data.get('feedback_text')
    attachments = data.get('attachments', [])
    
    # Удаляем сообщение со статусом прикреплений (если есть)
    last_message_id = data.get('last_attachment_message_id')
    if last_message_id:
        try:
            await callback.bot.delete_message(callback.message.chat.id, last_message_id)
        except Exception as e:
            print(f"Ошибка удаления сообщения со статусом прикреплений: {e}")
            # Игнорируем ошибки удаления
    
    if not direction_id or not feedback_text:
        await callback.answer("❌ Ошибка: данные заявки не найдены", show_alert=True)
        await state.clear()
        return
    
    # Обрабатываем направление
    if direction_id == "admin":
        direction_name = "Администрация"
        db_direction_id = None
    else:
        try:
            direction = await db.get_direction_by_id(direction_id)
            direction_name = direction[1] if direction else "Неизвестное направление"
            db_direction_id = direction_id
        except Exception as e:
            print(f"Ошибка получения направления {direction_id}: {e}")
            direction_name = "Неизвестное направление"
            db_direction_id = direction_id
    
    # Сохраняем заявку в базу
    try:
        message_id = await db.save_feedback_message(
            callback.from_user.id,
            callback.from_user.username,
            callback.from_user.first_name,
            feedback_text,
            db_direction_id
        )
        
        # Сохраняем прикрепления
        for attachment in attachments:
            try:
                await db.save_attachment(
                    message_id,
                    attachment['file_id'],
                    attachment['file_type'],
                    attachment['file_name'],
                    attachment['file_size'],
                    attachment['mime_type']
                )
            except Exception as e:
                print(f"Ошибка сохранения прикрепления {attachment['file_name']}: {e}")
                # Продолжаем сохранение других прикреплений
                
    except Exception as e:
        print(f"Ошибка сохранения заявки в базу данных: {e}")
        await callback.answer("❌ Ошибка сохранения заявки", show_alert=True)
        await state.clear()
        return
    
    # Определяем правильную клавиатуру для ответа
    try:
        is_admin = await db.is_admin(callback.from_user.id)
        is_teacher = await db.is_teacher(callback.from_user.id)
        
        if is_admin:
            keyboard = get_admin_keyboard()
        elif is_teacher:
            keyboard = get_teacher_keyboard()
        else:
            keyboard = get_main_keyboard()
    except Exception as e:
        print(f"Ошибка определения клавиатуры: {e}")
        keyboard = get_main_keyboard()  # По умолчанию
    
    # Формируем сообщение пользователю
    attachments_text = ""
    if attachments:
        attachments_text = f"\n📎 *Прикреплено файлов:* {len(attachments)}"
    
    if direction_id == "admin":
        user_message = (
            f"✅ *Заявка создана успешно!*\n\n"
            f"📝 *Номер заявки:* #{message_id}\n"
            f"👑 *Адресовано:* {direction_name}\n"
            f"📋 *Статус:* На рассмотрении{attachments_text}\n\n"
            f"💬 *Ваша заявка:*\n{feedback_text}\n\n"
            "⏳ Ваша заявка направлена администрации.\n"
            "📱 Ответ придёт в ближайшее время.\n"
            "❌ До получения ответа создание новых заявок недоступно."
        )
    else:
        user_message = (
            f"✅ *Заявка создана успешно!*\n\n"
            f"📝 *Номер заявки:* #{message_id}\n"
            f"📚 *Направление:* {direction_name}\n"
            f"📋 *Статус:* На рассмотрении{attachments_text}\n\n"
            f"💬 *Ваша заявка:*\n{feedback_text}\n\n"
            "⏳ Ваша заявка направлена преподавателю и администрации.\n"
            "📱 Ответ придёт в ближайшее время.\n"
            "❌ До получения ответа создание новых заявок недоступно."
        )
    
    await safe_edit_message(
        callback.message,
        user_message,
        parse_mode="Markdown"
    )
    
    # Отправляем клавиатуру отдельным сообщением
    try:
        await callback.message.answer(
            "Используйте кнопки меню для навигации.",
            reply_markup=keyboard
        )
    except Exception as e:
        print(f"Ошибка отправки клавиатуры: {e}")
        try:
            # Пытаемся отправить без клавиатуры
            await callback.message.answer("Используйте кнопки меню для навигации.")
        except Exception as e2:
            print(f"Ошибка отправки сообщения без клавиатуры: {e2}")
    
    # Теперь отправляем уведомления с прикреплениями
    try:
        await send_notifications_with_attachments(callback.bot, message_id, direction_id, direction_name, 
                                                callback.from_user, feedback_text, attachments)
    except Exception as e:
        print(f"Ошибка отправки уведомлений: {e}")
        # Продолжаем выполнение, даже если уведомления не отправились
    
    await state.clear()
    try:
        await callback.answer("✅ Заявка отправлена!")
    except Exception as e:
        print(f"Ошибка отправки callback answer: {e}")
        # Если не удалось отправить callback answer, ничего не делаем

# Дополнительные обработчики кнопок админской панели
@router.message(F.text == "🎫 Заявки")
async def admin_requests_button(message: Message):
    """Обработка кнопки Заявки"""
    if not await db.is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для выполнения этой команды.")
        return
    
    if message.chat.type != 'private':
        await message.answer("⚠️ Эта функция доступна только в личных сообщениях.")
        return
    
    # Переадресуем на обработчик из admin_handlers
    from admin_handlers import admin_requests_menu
    await admin_requests_menu(message)

@router.message(F.text == "📊 Статистика")
async def admin_statistics_button(message: Message):
    """Обработка кнопки Статистика"""
    if not await db.is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для выполнения этой команды.")
        return
    
    # Переадресуем на обработчик из admin_handlers
    from admin_handlers import admin_statistics_menu
    await admin_statistics_menu(message)

@router.message(F.text == "⚙️ Настройки")
async def admin_settings_button(message: Message):
    """Обработка кнопки Настройки"""
    if not await db.is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для выполнения этой команды.")
        return
    
    if message.chat.type != 'private':
        await message.answer("⚠️ Эта функция доступна только в личных сообщениях.")
        return
    
    # Переадресуем на обработчик из admin_handlers
    from admin_handlers import admin_settings_menu
    await admin_settings_menu(message)

# Обработчики кнопок для преподавателей
@router.message(F.text == "🎫 Мои заявки")
async def teacher_requests_button(message: Message):
    """Обработка кнопки Мои заявки"""
    if not await db.is_teacher(message.from_user.id):
        await message.answer("❌ У вас нет прав для выполнения этой команды.")
        return
    
    if message.chat.type != 'private':
        await message.answer("⚠️ Эта функция доступна только в личных сообщениях.")
        return
    
    # Переадресуем на обработчик из teacher_handlers
    from teacher_handlers import teacher_my_requests
    await teacher_my_requests(message)

@router.message(F.text == "📚 Мои направления")
async def teacher_directions_button(message: Message):
    """Обработка кнопки Мои направления"""
    if not await db.is_teacher(message.from_user.id):
        await message.answer("❌ У вас нет прав для выполнения этой команды.")
        return
    
    if message.chat.type != 'private':
        await message.answer("⚠️ Эта функция доступна только в личных сообщениях.")
        return
    
    # Переадресуем на обработчик из teacher_handlers
    from teacher_handlers import teacher_my_directions
    await teacher_my_directions(message)

# Управление администраторами перенесено в настройки

# Добавление админа
@router.callback_query(F.data == "add_admin")
async def add_admin_start(callback: CallbackQuery, state: FSMContext):
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав для выполнения этой команды.", show_alert=True)
        return
    
    await callback.message.answer(
        "👤 *Добавление администратора*\n\n"
        "Отправьте ID пользователя, которого хотите сделать администратором.\n"
        "ID можно получить, попросив пользователя написать боту /start",
        parse_mode="Markdown",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(AdminStates.waiting_for_admin_id)
    await callback.answer()

# Получение ID для добавления админа
@router.message(StateFilter(AdminStates.waiting_for_admin_id))
async def add_admin_process(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await message.answer("Отменено.", reply_markup=get_admin_keyboard())
        await state.clear()
        return
    
    try:
        user_id = int(message.text.strip())
        
        # Получаем информацию о пользователе через Telegram API
        try:
            user_info = await message.bot.get_chat(user_id)
            username = user_info.username
            first_name = user_info.first_name
        except Exception:
            # Если не удалось получить информацию о пользователе
            username = None
            first_name = "Новый админ"
        
        await db.add_admin(user_id, username, first_name, message.from_user.id)
        
        # Формируем сообщение с информацией о добавленном пользователе
        display_name = f"@{username}" if username else str(user_id)
        await message.answer(
            f"✅ Пользователь {display_name} (ID: {user_id}) добавлен в администраторы!",
            reply_markup=get_admin_keyboard()
        )
    except ValueError:
        await message.answer("❌ Неверный формат ID. Введите числовой ID пользователя.")
        return
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}", reply_markup=get_admin_keyboard())
    
    await state.clear()

# Удаление админа
@router.callback_query(F.data == "remove_admin")
async def remove_admin_start(callback: CallbackQuery, state: FSMContext):
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав для выполнения этой команды.", show_alert=True)
        return
    
    await callback.message.answer(
        "👤 *Удаление администратора*\n\n"
        "Отправьте ID пользователя, которого хотите удалить из администраторов.\n"
        "⚠️ *Внимание:* Вы не можете удалить самого себя!",
        parse_mode="Markdown",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(AdminStates.waiting_for_remove_admin_id)
    await callback.answer()

# Получение ID для удаления админа
@router.message(StateFilter(AdminStates.waiting_for_remove_admin_id))
async def remove_admin_process(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await message.answer("Отменено.", reply_markup=get_admin_keyboard())
        await state.clear()
        return
    
    try:
        user_id = int(message.text.strip())
        
        # Проверяем, что пользователь не пытается удалить самого себя
        if user_id == message.from_user.id:
            await message.answer("❌ Вы не можете удалить самого себя из администраторов!")
            return
        
        # Проверяем, является ли пользователь админом
        if not await db.is_admin(user_id):
            await message.answer("❌ Пользователь не является администратором.")
            return
        
        # Получаем информацию о пользователе для красивого сообщения
        try:
            user_info = await message.bot.get_chat(user_id)
            username = user_info.username
            display_name = f"@{username}" if username else str(user_id)
        except Exception:
            display_name = str(user_id)
        
        # Удаляем администратора
        await db.remove_admin(user_id)
        
        await message.answer(
            f"✅ Пользователь {display_name} (ID: {user_id}) удален из администраторов!",
            reply_markup=get_admin_keyboard()
        )
    except ValueError:
        await message.answer("❌ Неверный формат ID. Введите числовой ID пользователя.")
        return
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}", reply_markup=get_admin_keyboard())
    
    await state.clear()

# Список админов
@router.callback_query(F.data == "list_admins")
async def list_admins(callback: CallbackQuery):
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав для выполнения этой команды.", show_alert=True)
        return
    
    admins = await db.get_all_admins()
    
    if not admins:
        text = "👥 *Список администраторов пуст*"
    else:
        text = "👥 *Список администраторов:*\n\n"
        for user_id, username, first_name in admins:
            # Формируем отображаемое имя - приоритет username, если нет то ID
            if username:
                display_name = f"@{username}"
            else:
                display_name = f"{user_id}"
            
            text += f"• {display_name} - `{user_id}`\n"
    
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

# Обновление информации об админах
@router.callback_query(F.data == "update_admins_info")
async def update_admins_info(callback: CallbackQuery):
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав для выполнения этой команды.", show_alert=True)
        return
    
    await callback.answer("🔄 Обновляю информацию об администраторах...")
    
    admins = await db.get_all_admins()
    updated_count = 0
    
    for user_id, old_username, old_first_name in admins:
        try:
            # Получаем актуальную информацию о пользователе
            user_info = await callback.bot.get_chat(user_id)
            new_username = user_info.username
            new_first_name = user_info.first_name
            
            # Обновляем только если информация изменилась
            if new_username != old_username or new_first_name != old_first_name:
                await db.update_admin_info(user_id, new_username, new_first_name)
                updated_count += 1
                
        except Exception:
            # Пропускаем пользователей, информацию о которых не удалось получить
            continue
    
    if updated_count > 0:
        await callback.message.answer(
            f"✅ Информация обновлена для {updated_count} администраторов!",
            reply_markup=get_admin_keyboard()
        )
    else:
        await callback.message.answer(
            "ℹ️ Информация об администраторах актуальна.",
            reply_markup=get_admin_keyboard()
        )

# Возврат к управлению админами (теперь перенаправляет к настройкам)
@router.callback_query(F.data == "back_to_admin_management")
async def back_to_admin_management(callback: CallbackQuery):
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав для выполнения этой команды.", show_alert=True)
        return
    
    from chat_handler import ChatBehavior
    from enhanced_keyboards import get_settings_keyboard
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

# Настройки уведомлений - теперь перенаправляет к настройкам
@router.callback_query(F.data == "notification_settings")
async def notification_settings(callback: CallbackQuery):
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав для выполнения этой команды.", show_alert=True)
        return
    
    from chat_handler import ChatBehavior
    from enhanced_keyboards import get_settings_keyboard
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

# Добавление чата для уведомлений
@router.callback_query(F.data == "add_notification_chat")
async def add_notification_chat_start(callback: CallbackQuery, state: FSMContext):
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав для выполнения этой команды.", show_alert=True)
        return
    
    await callback.message.answer(
        "📢 *Добавление чата для уведомлений*\n\n"
        "Отправьте ID чата, в который должны приходить уведомления об обратной связи.\n\n"
        "🔍 *Как получить ID чата:*\n"
        "• 🆕 *Легкий способ:* Добавьте бота в группу - он автоматически покажет ID\n"
        "• Используйте команду `/chatid` в любом чате с ботом\n"
        "• ID чата можно узнать через специальных ботов (@userinfobot)\n"
        "• ID группы обычно отрицательное число\n\n"
        "💡 *Примеры:*\n"
        "• `-1001234567890` (группа)\n"
        "• `123456789` (личный чат)",
        parse_mode="Markdown",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(NotificationStates.waiting_for_chat_id)
    await callback.answer()

# Получение ID чата для добавления
@router.message(StateFilter(NotificationStates.waiting_for_chat_id))
async def add_notification_chat_process(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await message.answer("Отменено.", reply_markup=get_admin_keyboard())
        await state.clear()
        return
    
    try:
        chat_id = int(message.text.strip())
        
        # Пытаемся получить информацию о чате
        try:
            chat_info = await message.bot.get_chat(chat_id)
            chat_title = chat_info.title or f"Личный чат {chat_info.first_name}"
            chat_type = chat_info.type
        except Exception:
            # Если не удалось получить информацию о чате
            chat_title = f"Чат {chat_id}"
            chat_type = "unknown"
        
        # Проверяем, не добавлен ли уже этот чат
        if await db.is_notification_chat(chat_id):
            await message.answer(
                f"⚠️ Чат `{chat_id}` уже добавлен в список уведомлений!",
                parse_mode="Markdown",
                reply_markup=get_admin_keyboard()
            )
            await state.clear()
            return
        
        await db.add_notification_chat(chat_id, chat_title, chat_type, message.from_user.id)
        
        await message.answer(
            f"✅ Чат добавлен!\n\n"
            f"📋 *Название:* {chat_title}\n"
            f"🆔 *ID:* `{chat_id}`\n"
            f"📱 *Тип:* {chat_type}\n\n"
            f"Теперь уведомления об обратной связи будут приходить в этот чат.",
            parse_mode="Markdown",
            reply_markup=get_admin_keyboard()
        )
    except ValueError:
        await message.answer(
            "❌ Неверный формат ID чата. Введите числовой ID.\n\n"
            "Например: `-1001234567890` или `123456789`"
        )
        return
    except Exception as e:
        await message.answer(
            f"❌ Ошибка при добавлении чата: {str(e)}",
            reply_markup=get_admin_keyboard()
        )
    
    await state.clear()

# Список чатов для уведомлений
@router.callback_query(F.data == "list_notification_chats")
async def list_notification_chats(callback: CallbackQuery):
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав для выполнения этой команды.", show_alert=True)
        return
    
    chats = await db.get_notification_chats()
    
    if not chats:
        text = (
            "📢 *Чаты для уведомлений*\n\n"
            "Список пуст. Добавьте чаты для получения уведомлений об обратной связи."
        )
        keyboard = get_back_to_notification_settings_keyboard()
    else:
        text = "📢 *Чаты для уведомлений:*\n\n"
        for chat_id, chat_title, chat_type in chats:
            status = "🔔 Активен"
            text += f"• {chat_title}\n"
            text += f"  ID: `{chat_id}` | {chat_type} | {status}\n\n"
        
        # Создаем клавиатуру с чатами
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        from aiogram.types import InlineKeyboardButton
        builder = InlineKeyboardBuilder()
        
        for chat_id, chat_title, chat_type in chats:
            # Обрезаем длинные названия
            button_text = chat_title[:30] + "..." if len(chat_title) > 30 else chat_title
            builder.add(InlineKeyboardButton(
                text=f"⚙️ {button_text}",
                callback_data=f"manage_chat:{chat_id}"
            ))
        
        builder.add(InlineKeyboardButton(
            text="⬅️ Назад к настройкам",
            callback_data="settings_notifications"
        ))
        builder.adjust(1)
        keyboard = builder.as_markup()
    
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=keyboard
    )
    await callback.answer()

# Управление конкретным чатом
@router.callback_query(F.data.startswith("manage_chat:"))
async def manage_notification_chat(callback: CallbackQuery):
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав для выполнения этой команды.", show_alert=True)
        return
    
    chat_id = int(callback.data.split(":", 1)[1])
    
    # Получаем информацию о чате из БД
    chats = await db.get_notification_chats()
    chat_info = None
    for c_id, c_title, c_type in chats:
        if c_id == chat_id:
            chat_info = (c_id, c_title, c_type)
            break
    
    if not chat_info:
        await callback.answer("❌ Чат не найден", show_alert=True)
        return
    
    chat_id, chat_title, chat_type = chat_info
    is_active = await db.is_notification_chat(chat_id)
    
    status = "🔔 Активен" if is_active else "🔇 Отключен"
    text = (
        f"⚙️ *Управление чатом*\n\n"
        f"📋 *Название:* {chat_title}\n"
        f"🆔 *ID:* `{chat_id}`\n"
        f"📱 *Тип:* {chat_type}\n"
        f"📊 *Статус:* {status}\n\n"
        f"Выберите действие:"
    )
    
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_notification_chat_actions_keyboard(chat_id, is_active)
    )
    await callback.answer()

# Включение/отключение чата
@router.callback_query(F.data.startswith("toggle_chat:"))
async def toggle_notification_chat(callback: CallbackQuery):
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав для выполнения этой команды.", show_alert=True)
        return
    
    parts = callback.data.split(":")
    chat_id = int(parts[1])
    is_active = bool(int(parts[2]))
    
    await db.toggle_notification_chat(chat_id, is_active)
    
    action = "включен" if is_active else "отключен"
    await callback.answer(f"✅ Чат {action}!")
    
    # Обновляем сообщение
    await manage_notification_chat(callback)

# Удаление чата
@router.callback_query(F.data.startswith("remove_chat:"))
async def remove_notification_chat(callback: CallbackQuery):
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав для выполнения этой команды.", show_alert=True)
        return
    
    chat_id = int(callback.data.split(":", 1)[1])
    
    await db.remove_notification_chat(chat_id)
    
    await callback.answer("✅ Чат удален из списка уведомлений!")
    
    # Возвращаемся к списку чатов
    await list_notification_chats(callback)

# Команда просмотра переписки с пользователем (только для админов)
@router.message(Command("msg"))
async def show_user_conversation(message: Message):
    if not await db.is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для выполнения этой команды.")
        return
    
    # Парсим команду: /msg 123456789
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer(
            "❌ Неверный формат команды.\n"
            "Используйте: `/msg ID_пользователя`\n"
            "Например: `/msg 123456789`",
            parse_mode="Markdown"
        )
        return
    
    try:
        user_id = int(parts[1])
    except ValueError:
        await message.answer("❌ Неверный ID пользователя. Должно быть число.")
        return
    
    # Получаем переписку
    conversation = await db.get_user_conversation(user_id)
    
    if not conversation:
        await message.answer(f"❌ Переписка с пользователем `{user_id}` не найдена.", parse_mode="Markdown")
        return
    
    # Формируем текст переписки
    text = f"🎫 *Заявки пользователя* `{user_id}`\n\n"
    
    for msg_id, msg_text, created_at, is_answered, answer_text, answered_at, answered_by, status in conversation:
        # Форматируем дату
        from datetime import datetime
        created_date = datetime.fromisoformat(created_at).strftime("%d.%m.%Y %H:%M")
        
        # Определяем статус заявки
        if status == 'closed' or is_answered:
            status_text = "🔒 Закрыта"
            status_emoji = "✅"
        else:
            status_text = "🔓 Активна"
            status_emoji = "⏳"
        
        text += f"{status_emoji} *Заявка #{msg_id}* ({created_date})\n"
        text += f"📋 *Статус:* {status_text}\n"
        text += f"👤 *Пользователь:* {msg_text}\n"
        
        if is_answered and answer_text:
            answered_date = datetime.fromisoformat(answered_at).strftime("%d.%m.%Y %H:%M") if answered_at else "Неизвестно"
            text += f"💬 *Ответ админа* ({answered_date}): {answer_text}\n"
        else:
            text += "⏳ *Ожидает ответа*\n"
        
        text += "\n" + "─" * 40 + "\n\n"
    
    # Разбиваем длинные сообщения на части
    max_length = 4000
    if len(text) > max_length:
        parts = []
        current_part = ""
        
        for line in text.split('\n'):
            if len(current_part + line + '\n') > max_length:
                if current_part:
                    parts.append(current_part)
                    current_part = line + '\n'
                else:
                    parts.append(line[:max_length])
            else:
                current_part += line + '\n'
        
        if current_part:
            parts.append(current_part)
        
        # Отправляем по частям
        for i, part in enumerate(parts):
            if i == 0:
                await message.answer(part, parse_mode="Markdown")
            else:
                await message.answer(f"*Продолжение переписки...*\n\n{part}", parse_mode="Markdown")
    else:
        await message.answer(text, parse_mode="Markdown")

# Управление преподавателями перенесено в настройки

# Управление преподавателями (callback) - теперь перенаправляет к настройкам
@router.callback_query(F.data == "teacher_management")
async def teacher_management(callback: CallbackQuery):
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав для выполнения этой команды.", show_alert=True)
        return
    
    from chat_handler import ChatBehavior
    from enhanced_keyboards import get_settings_keyboard
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

# Добавление преподавателя
@router.callback_query(F.data == "add_teacher")
async def add_teacher_start(callback: CallbackQuery, state: FSMContext):
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав для выполнения этой команды.", show_alert=True)
        return
    
    await callback.message.answer(
        "👨‍🏫 *Добавление преподавателя*\n\n"
        "Отправьте ID пользователя, которого хотите назначить преподавателем.\n"
        "ID можно получить, попросив пользователя написать боту /start",
        parse_mode="Markdown",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(TeacherStates.waiting_for_teacher_id)
    await callback.answer()

# Получение ID для добавления преподавателя
@router.message(StateFilter(TeacherStates.waiting_for_teacher_id))
async def add_teacher_process(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await message.answer("Отменено.", reply_markup=get_admin_keyboard())
        await state.clear()
        return
    
    try:
        user_id = int(message.text.strip())
        
        # Получаем информацию о пользователе через Telegram API
        try:
            user_info = await message.bot.get_chat(user_id)
            username = user_info.username
            first_name = user_info.first_name
        except Exception:
            username = None
            first_name = "Новый преподаватель"
        
        await db.add_teacher(user_id, username, first_name, message.from_user.id)
        
        display_name = f"@{username}" if username else str(user_id)
        await message.answer(
            f"✅ Пользователь {display_name} (ID: {user_id}) назначен преподавателем!",
            reply_markup=get_admin_keyboard()
        )
    except ValueError:
        await message.answer("❌ Неверный формат ID. Введите числовой ID пользователя.")
        return
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}", reply_markup=get_admin_keyboard())
    
    await state.clear()

# Удаление преподавателя
@router.callback_query(F.data == "remove_teacher")
async def remove_teacher_start(callback: CallbackQuery, state: FSMContext):
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав для выполнения этой команды.", show_alert=True)
        return
    
    await callback.message.answer(
        "👨‍🏫 *Удаление преподавателя*\n\n"
        "Отправьте ID преподавателя, которого хотите удалить.\n"
        "⚠️ *Внимание:* Будут удалены все привязки к направлениям!",
        parse_mode="Markdown",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(TeacherStates.waiting_for_remove_teacher_id)
    await callback.answer()

# Получение ID для удаления преподавателя
@router.message(StateFilter(TeacherStates.waiting_for_remove_teacher_id))
async def remove_teacher_process(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await message.answer("Отменено.", reply_markup=get_admin_keyboard())
        await state.clear()
        return
    
    try:
        user_id = int(message.text.strip())
        
        if not await db.is_teacher(user_id):
            await message.answer("❌ Пользователь не является преподавателем.")
            return
        
        try:
            user_info = await message.bot.get_chat(user_id)
            username = user_info.username
            display_name = f"@{username}" if username else str(user_id)
        except Exception:
            display_name = str(user_id)
        
        await db.remove_teacher(user_id)
        
        await message.answer(
            f"✅ Пользователь {display_name} (ID: {user_id}) удален из преподавателей!",
            reply_markup=get_admin_keyboard()
        )
    except ValueError:
        await message.answer("❌ Неверный формат ID. Введите числовой ID пользователя.")
        return
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}", reply_markup=get_admin_keyboard())
    
    await state.clear()

# Список преподавателей
@router.callback_query(F.data == "list_teachers")
async def list_teachers(callback: CallbackQuery):
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав для выполнения этой команды.", show_alert=True)
        return
    
    teachers = await db.get_all_teachers()
    
    if not teachers:
        text = "👨‍🏫 *Список преподавателей пуст*"
    else:
        text = "👨‍🏫 *Список преподавателей:*\n\n"
        for user_id, username, first_name in teachers:
            if username:
                display_name = f"@{username}"
            else:
                display_name = f"{user_id}"
            
            # Получаем направления преподавателя
            directions = await db.get_directions_for_teacher(user_id)
            direction_names = [d[1] for d in directions] if directions else ["Нет привязок"]
            
            text += f"• {display_name} - `{user_id}`\n"
            text += f"  📚 Направления: {', '.join(direction_names[:2])}{'...' if len(direction_names) > 2 else ''}\n\n"
    
    await callback.message.edit_text(
        text, 
        parse_mode="Markdown",
        reply_markup=get_back_to_teacher_management_keyboard()
    )
    await callback.answer()

# Управление привязками направлений
@router.callback_query(F.data == "teacher_directions")
async def teacher_directions(callback: CallbackQuery):
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав для выполнения этой команды.", show_alert=True)
        return
    
    directions = await db.get_all_directions()
    
    if not directions:
        await callback.message.edit_text(
            "📚 *Привязки к направлениям*\n\n"
            "❌ Направления не найдены.\n"
            "Направления автоматически загружаются из расписания при запуске бота.",
            parse_mode="Markdown",
            reply_markup=get_back_to_teacher_management_keyboard()
        )
        await callback.answer()
        return
    
    await callback.message.edit_text(
        "🔗 *Привязки преподавателей к направлениям*\n\n"
        "Выберите направление для управления преподавателями:",
        parse_mode="Markdown",
        reply_markup=get_directions_list_keyboard(directions)
    )
    await callback.answer()

# Управление конкретным направлением
@router.callback_query(F.data.startswith("manage_direction:"))
async def manage_direction(callback: CallbackQuery):
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав для выполнения этой команды.", show_alert=True)
        return
    
    direction_id = int(callback.data.split(":", 1)[1])
    
    # Получаем информацию о направлении
    direction = await db.get_direction_by_id(direction_id)
    if not direction:
        await callback.answer("❌ Направление не найдено", show_alert=True)
        return
    
    direction_name = direction[1]
    
    # Получаем преподавателей направления
    teachers = await db.get_teachers_for_direction(direction_id)
    
    # Получаем всех преподавателей
    all_teachers = await db.get_all_teachers()
    
    if not all_teachers:
        await callback.message.edit_text(
            f"📚 *Направление:* {direction_name}\n\n"
            "❌ Преподаватели не найдены.\n"
            "Сначала добавьте преподавателей в систему.",
            parse_mode="Markdown",
            reply_markup=get_back_to_teacher_management_keyboard()
        )
        await callback.answer()
        return
    
    # Формируем текст с текущими привязками
    text = f"📚 *Направление:* {direction_name}\n\n"
    
    if teachers:
        text += "👨‍🏫 *Назначенные преподаватели:*\n"
        for teacher_id, username, first_name in teachers:
            display_name = f"@{username}" if username else f"ID{teacher_id}"
            text += f"• {display_name}\n"
        text += "\n"
    else:
        text += "❌ *Преподаватели не назначены*\n\n"
    
    text += "💡 *Управление:*\n"
    text += "• ❌ - отвязать преподавателя\n"
    text += "• ➕ - привязать преподавателя"
    
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_direction_teachers_keyboard(direction_id, teachers, all_teachers)
    )
    await callback.answer()

# Привязка преподавателя к направлению
@router.callback_query(F.data.startswith("assign_teacher:"))
async def assign_teacher(callback: CallbackQuery):
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав для выполнения этой команды.", show_alert=True)
        return
    
    parts = callback.data.split(":")
    direction_id = int(parts[1])
    teacher_id = int(parts[2])
    
    await db.assign_teacher_to_direction(teacher_id, direction_id, callback.from_user.id)
    
    await callback.answer("✅ Преподаватель привязан к направлению!")
    
    # Обновляем сообщение
    await manage_direction(callback)

# Отвязка преподавателя от направления
@router.callback_query(F.data.startswith("unassign_teacher:"))
async def unassign_teacher(callback: CallbackQuery):
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав для выполнения этой команды.", show_alert=True)
        return
    
    parts = callback.data.split(":")
    direction_id = int(parts[1])
    teacher_id = int(parts[2])
    
    await db.remove_teacher_from_direction(teacher_id, direction_id)
    
    await callback.answer("✅ Преподаватель отвязан от направления!")
    
    # Обновляем сообщение
    await manage_direction(callback)

# Обработка текстовых сообщений в состоянии ожидания (только в ЛС)
@router.message(F.chat.type == "private")
async def handle_text_messages(message: Message):
    # Если админ или преподаватель отвечает reply на сообщение бота (в ЛС или группе)
    if message.reply_to_message and message.reply_to_message.from_user.id == message.bot.id:
        # Проверяем, что отвечающий - админ или преподаватель
        is_admin = await db.is_admin(message.from_user.id)
        is_teacher = await db.is_teacher(message.from_user.id)
        
        if is_admin or is_teacher:
            # Ищем номер сообщения в тексте
            reply_text = message.reply_to_message.text or ""
            match = re.search(r'#(\d+)', reply_text)
            if match:
                message_id = int(match.group(1))
                reply_content = message.text
                
                # Получаем исходную заявку
                feedback_msg = await db.get_feedback_message(message_id)
                if feedback_msg:
                    user_id = feedback_msg[1]
                    original_text = feedback_msg[4]
                    is_answered = feedback_msg[6]
                    status = feedback_msg[7] if len(feedback_msg) > 7 else 'active'
                    
                    # Проверяем, что заявка ещё активна
                    if status == 'closed' or is_answered:
                        # Определяем правильную клавиатуру для отвечающего
                        if is_admin:
                            closed_keyboard = get_admin_keyboard()
                        elif is_teacher:
                            closed_keyboard = get_teacher_keyboard()
                        else:
                            closed_keyboard = get_admin_keyboard()  # по умолчанию
                        
                        await message.answer(
                            f"⚠️ Заявка #{message_id} уже закрыта.",
                            reply_markup=closed_keyboard
                        )
                        return
                    
                    # Если отвечает преподаватель, проверяем права на данную заявку
                    if is_teacher and not is_admin:
                        can_reply = await db.can_teacher_reply_to_request(message.from_user.id, message_id)
                        if not can_reply:
                            # Показываем клавиатуру преподавателя
                            teacher_no_rights_keyboard = get_teacher_keyboard()
                            
                            await message.answer(
                                f"❌ У вас нет прав для ответа на заявку #{message_id}.\n"
                                "Вы можете отвечать только на заявки по направлениям, к которым вы привязаны.",
                                reply_markup=teacher_no_rights_keyboard
                            )
                            return
                    
                    try:
                        # Определяем роль отвечающего (переменные уже определены выше)
                        
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
                        
                        # Определяем правильную клавиатуру для отвечающего
                        if is_admin:
                            response_keyboard = get_admin_keyboard()
                        elif is_teacher:
                            response_keyboard = get_teacher_keyboard()
                        else:
                            response_keyboard = get_admin_keyboard()  # по умолчанию
                        
                        await message.answer(
                            f"✅ Ответ на заявку #{message_id} отправлен! Заявка закрыта.",
                            reply_markup=response_keyboard
                        )
                        
                    except Exception as e:
                        # Определяем правильную клавиатуру для отвечающего
                        if is_admin:
                            error_keyboard = get_admin_keyboard()
                        elif is_teacher:
                            error_keyboard = get_teacher_keyboard()
                        else:
                            error_keyboard = get_admin_keyboard()  # по умолчанию
                        
                        await message.answer(
                            f"❌ Ошибка отправки ответа: {str(e)}",
                            reply_markup=error_keyboard
                        )
                else:
                    # Определяем правильную клавиатуру для отвечающего
                    if is_admin:
                        not_found_keyboard = get_admin_keyboard()
                    elif is_teacher:
                        not_found_keyboard = get_teacher_keyboard()
                    else:
                        not_found_keyboard = get_admin_keyboard()  # по умолчанию
                    
                    await message.answer(
                        f"❌ Заявка #{message_id} не найдена.",
                        reply_markup=not_found_keyboard
                    )

def escape_markdown(text):
    """Экранирует специальные символы для Markdown"""
    if not text:
        return ""
    return text.replace('*', '\\*').replace('_', '\\_').replace('[', '\\[').replace(']', '\\]').replace('`', '\\`')

# Функция для отправки уведомлений с прикреплениями
async def send_notifications_with_attachments(bot, message_id, direction_id, direction_name, user, feedback_text, attachments):
    """Отправляет уведомления о новой заявке с прикреплениями"""
    
    # Формируем базовый текст уведомления
    base_notification = (
        f"🎫 *Новая заявка*\n\n"
        f"👤 *От:* {user.first_name}"
    )
    if user.username:
        base_notification += f" (@{user.username})"
    
    base_notification += f"\n🆔 *ID пользователя:* `{user.id}`\n"
    base_notification += f"📝 *Номер заявки:* #{message_id}\n"
    
    # Добавляем информацию о направлении
    if direction_id == "admin":
        base_notification += f"👑 *Адресовано:* {direction_name}\n"
    else:
        base_notification += f"📚 *Направление:* {direction_name}\n"
    
    base_notification += f"📋 *Статус:* На рассмотрении\n"
    
    # Добавляем информацию о прикреплениях
    if attachments:
        base_notification += f"📎 *Прикреплено файлов:* {len(attachments)}\n"
        # Добавляем список файлов
        for i, attachment in enumerate(attachments[:3]):  # Показываем первые 3 файла
            safe_name = escape_markdown(attachment['file_name'])
            base_notification += f"   • `{safe_name}`\n"
        if len(attachments) > 3:
            base_notification += f"   • ... и еще {len(attachments) - 3} файл(ов)\n"
    
    base_notification += f"\n💬 *Текст заявки:*\n{escape_markdown(feedback_text)}\n\n"
    base_notification += "💡 *Для ответа и закрытия заявки:* просто ответьте на это сообщение (reply/свайп)\n"
    base_notification += "✅ После ответа заявка будет автоматически закрыта"
    
    # Отправляем преподавателям только если это НЕ заявка для администрации
    if direction_id != "admin":
        teachers = await db.get_teachers_for_direction(direction_id)
        
        if teachers:
            teacher_text = f"👨‍🏫 *Заявка по вашему направлению*\n\n" + base_notification
            for teacher_id, teacher_username, teacher_first_name in teachers:
                try:
                    # Отправляем текст уведомления
                    await bot.send_message(teacher_id, teacher_text, parse_mode="Markdown")
                    
                    # Отправляем прикрепления
                    await send_attachments_group(bot, teacher_id, attachments)
                        
                except Exception as e:
                    print(f"Ошибка отправки преподавателю {teacher_id}: {e}")
    
    # Отправляем администраторам
    if direction_id == "admin":
        admin_text = f"👑 *Заявка для администрации*\n\n" + base_notification
    else:
        admin_text = f"👑 *Заявка для администрации* (дубликат)\n\n" + base_notification
    
    # Отправляем в настроенные чаты для админов
    notification_chats = await db.get_notification_chats()
    if notification_chats:
        for chat_id, chat_title, chat_type in notification_chats:
            try:
                # Отправляем текст уведомления
                sent_message = await bot.send_message(chat_id, admin_text, parse_mode="Markdown")
                # Сохраняем message_id отправленного уведомления
                await db.save_notification_message(message_id, chat_id, sent_message.message_id)
                
                # Отправляем прикрепления
                await send_attachments_group(bot, chat_id, attachments)
                    
            except Exception as e:
                print(f"Ошибка отправки в чат {chat_id} ({chat_title}): {e}")
    else:
        # Если чаты не настроены - отправляем всем админам в ЛС
        admins = await db.get_all_admins()
        for admin_id, _, _ in admins:
            try:
                # Отправляем текст уведомления
                sent_message = await bot.send_message(admin_id, admin_text, parse_mode="Markdown")
                # Сохраняем message_id отправленного уведомления
                await db.save_notification_message(message_id, admin_id, sent_message.message_id)
                
                # Отправляем прикрепления
                await send_attachments_group(bot, admin_id, attachments)
                    
            except Exception as e:
                print(f"Ошибка отправки админу {admin_id}: {e}")

async def send_attachments_group(bot, user_id, attachments):
    """Отправляет группу прикрепленных файлов одним сообщением"""
    if not attachments:
        return
        
    try:
        from aiogram.types import InputMediaPhoto, InputMediaDocument, InputMediaVideo, InputMediaAudio
        
        media_group = []
        
        for i, attachment in enumerate(attachments):
            file_type = attachment['file_type']
            file_id = attachment['file_id']
            safe_file_name = attachment['file_name'].replace('*', '\\*').replace('_', '\\_').replace('[', '\\[').replace(']', '\\]').replace('`', '\\`')
            
            # Добавляем caption только к первому файлу
            caption = f"📎 Прикрепленные файлы к заявке:\n" if i == 0 else None
            
            if file_type == "photo":
                media_item = InputMediaPhoto(
                    media=file_id,
                    caption=caption,
                    parse_mode="Markdown"
                )
            elif file_type == "document":
                media_item = InputMediaDocument(
                    media=file_id,
                    caption=caption,
                    parse_mode="Markdown"
                )
            elif file_type == "video":
                media_item = InputMediaVideo(
                    media=file_id,
                    caption=caption,
                    parse_mode="Markdown"
                )
            elif file_type == "audio":
                media_item = InputMediaAudio(
                    media=file_id,
                    caption=caption,
                    parse_mode="Markdown"
                )
            else:
                # Для voice и video_note отправляем отдельно, так как они не поддерживаются в медиагруппе
                continue
                
            media_group.append(media_item)
        
        # Отправляем медиагруппу
        if media_group:
            try:
                await bot.send_media_group(user_id, media_group)
            except Exception as e:
                print(f"Ошибка отправки медиагруппы пользователю {user_id}: {e}")
                # Если медиагруппа не удалась, отправляем файлы по одному
                for attachment in attachments:
                    await send_single_attachment(bot, user_id, attachment)
                return
        
        # Отправляем voice и video_note отдельно
        for attachment in attachments:
            file_type = attachment['file_type']
            file_id = attachment['file_id']
            safe_file_name = attachment['file_name'].replace('*', '\\*').replace('_', '\\_').replace('[', '\\[').replace(']', '\\]').replace('`', '\\`')
            
            try:
                if file_type == "voice":
                    await bot.send_voice(user_id, file_id, caption=f"📎 {safe_file_name}", parse_mode="Markdown")
                elif file_type == "video_note":
                    await bot.send_video_note(user_id, file_id)
            except Exception as e:
                print(f"Ошибка отправки {file_type} пользователю {user_id}: {e}")
                
    except Exception as e:
        print(f"Ошибка отправки медиагруппы пользователю {user_id}: {e}")
        # Если медиагруппа не удалась, отправляем файлы по одному
        for attachment in attachments:
            await send_single_attachment(bot, user_id, attachment)

async def send_single_attachment(bot, user_id, attachment):
    """Отправляет один прикрепленный файл пользователю"""
    try:
        file_type = attachment['file_type']
        file_id = attachment['file_id']
        
        # Экранируем специальные символы в названии файла
        safe_file_name = attachment['file_name'].replace('*', '\\*').replace('_', '\\_').replace('[', '\\[').replace(']', '\\]').replace('`', '\\`')
        caption = f"📎 {safe_file_name}"
        
        if file_type == "photo":
            await bot.send_photo(user_id, file_id, caption=caption, parse_mode="Markdown")
        elif file_type == "document":
            await bot.send_document(user_id, file_id, caption=caption, parse_mode="Markdown")
        elif file_type == "video":
            await bot.send_video(user_id, file_id, caption=caption, parse_mode="Markdown")
        elif file_type == "audio":
            await bot.send_audio(user_id, file_id, caption=caption, parse_mode="Markdown")
        elif file_type == "voice":
            await bot.send_voice(user_id, file_id, caption=caption, parse_mode="Markdown")
        elif file_type == "video_note":
            await bot.send_video_note(user_id, file_id)
            
    except Exception as e:
        print(f"Ошибка отправки прикрепления {attachment['file_name']} пользователю {user_id}: {e}")
