"""
Расширенные клавиатуры для разных типов чатов
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from chat_handler import ChatType

def get_keyboard_for_chat_type(chat_type: ChatType, user_id: int = None):
    """Получить клавиатуру в зависимости от типа чата"""
    
    if chat_type == ChatType.PRIVATE_USER:
        return get_user_keyboard()
    
    elif chat_type == ChatType.PRIVATE_ADMIN:
        return get_admin_keyboard()
    
    elif chat_type == ChatType.PRIVATE_TEACHER:
        return get_teacher_keyboard()
    
    elif chat_type == ChatType.PUBLIC_GROUP:
        return get_public_group_keyboard()
    
    elif chat_type == ChatType.ADMIN_GROUP:
        return get_admin_group_keyboard()
    
    elif chat_type == ChatType.TEACHER_GROUP:
        return get_teacher_group_keyboard()
    
    return get_user_keyboard()  # По умолчанию

def get_user_keyboard():
    """Клавиатура для обычного пользователя в личных сообщениях"""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="📅 Расписание"))
    builder.add(KeyboardButton(text="💬 Обратная связь"))
    builder.add(KeyboardButton(text="ℹ️ Помощь"))
    builder.adjust(2, 1)
    return builder.as_markup(resize_keyboard=True)

def get_admin_keyboard():
    """Расширенная клавиатура для администратора"""
    builder = ReplyKeyboardBuilder()
    
    # Основные функции
    builder.add(KeyboardButton(text="📅 Расписание"))
    builder.add(KeyboardButton(text="💬 Обратная связь"))
    
    # Админские функции
    builder.add(KeyboardButton(text="🎫 Заявки"))
    builder.add(KeyboardButton(text="📊 Статистика"))
    builder.add(KeyboardButton(text="⚙️ Настройки"))
    builder.add(KeyboardButton(text="ℹ️ Помощь"))
    
    builder.adjust(2, 2, 2)
    return builder.as_markup(resize_keyboard=True)

def get_teacher_keyboard():
    """Клавиатура для преподавателя"""
    builder = ReplyKeyboardBuilder()
    
    # Основные функции
    builder.add(KeyboardButton(text="📅 Расписание"))
    builder.add(KeyboardButton(text="💬 Обратная связь"))
    
    # Преподавательские функции
    builder.add(KeyboardButton(text="🎫 Мои заявки"))
    builder.add(KeyboardButton(text="📚 Мои направления"))
    builder.add(KeyboardButton(text="ℹ️ Помощь"))
    
    builder.adjust(2, 2, 1)
    return builder.as_markup(resize_keyboard=True)

def get_public_group_keyboard():
    """Inline клавиатура для публичной группы"""
    builder = InlineKeyboardBuilder()
    
    builder.add(InlineKeyboardButton(text="📅 Расписание", callback_data="schedule"))
    builder.add(InlineKeyboardButton(text="🆔 ID чата", callback_data="show_chat_id"))
    builder.add(InlineKeyboardButton(text="ℹ️ О боте", callback_data="bot_info"))
    # TODO: Заменить на реальный username бота
    # builder.add(InlineKeyboardButton(text="💬 Написать в ЛС", url="https://t.me/YOUR_BOT_USERNAME"))
    
    builder.adjust(2, 2)
    return builder.as_markup()

def get_admin_group_keyboard():
    """Inline клавиатура для админской группы"""
    builder = InlineKeyboardBuilder()
    
    builder.add(InlineKeyboardButton(text="🎫 Активные заявки", callback_data="active_requests"))
    builder.add(InlineKeyboardButton(text="📊 Статистика", callback_data="group_statistics"))
    builder.add(InlineKeyboardButton(text="📅 Расписание", callback_data="quick_schedule"))
    builder.add(InlineKeyboardButton(text="⚙️ Настройки", callback_data="group_settings"))
    
    builder.adjust(2, 2)
    return builder.as_markup()

def get_teacher_group_keyboard():
    """Inline клавиатура для преподавательской группы"""
    builder = InlineKeyboardBuilder()
    
    builder.add(InlineKeyboardButton(text="🎫 Заявки по направлениям", callback_data="direction_requests"))
    builder.add(InlineKeyboardButton(text="📚 Расписание направлений", callback_data="direction_schedule"))
    builder.add(InlineKeyboardButton(text="📊 Статистика", callback_data="teacher_statistics"))
    
    builder.adjust(2, 1)
    return builder.as_markup()

# Специальные клавиатуры для новых функций

def get_quick_schedule_keyboard():
    """Клавиатура быстрого выбора расписания"""
    builder = InlineKeyboardBuilder()
    
    # Популярные направления или сегодняшний день
    builder.add(InlineKeyboardButton(text="📅 Сегодня", callback_data="schedule_today"))
    builder.add(InlineKeyboardButton(text="📅 Завтра", callback_data="schedule_tomorrow"))
    builder.add(InlineKeyboardButton(text="📋 Все направления", callback_data="schedule_all"))
    builder.add(InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_group_menu"))
    
    builder.adjust(2, 1, 1)
    return builder.as_markup()

def get_admin_requests_keyboard():
    """Клавиатура для управления заявками админом"""
    builder = InlineKeyboardBuilder()
    
    builder.add(InlineKeyboardButton(text="🔓 Активные заявки", callback_data="requests_active"))
    builder.add(InlineKeyboardButton(text="🔒 Закрытые заявки", callback_data="requests_closed"))
    builder.add(InlineKeyboardButton(text="📊 По направлениям", callback_data="requests_by_direction"))
    builder.add(InlineKeyboardButton(text="⏰ Недавние", callback_data="requests_recent"))
    builder.add(InlineKeyboardButton(text="🔍 Поиск", callback_data="requests_search"))
    builder.add(InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_group_menu"))
    
    builder.adjust(2, 2, 1, 1)
    return builder.as_markup()

def get_request_detail_keyboard(request_id: int, user_id: int, is_active: bool = True):
    """Клавиатура для детального просмотра заявки"""
    builder = InlineKeyboardBuilder()
    
    if is_active:
        builder.add(InlineKeyboardButton(text="💬 Ответить", callback_data=f"reply_request:{request_id}"))
    
    builder.add(InlineKeyboardButton(text="⬅️ Назад к списку", callback_data="requests_active"))
    
    if is_active:
        builder.adjust(1, 1)
    else:
        builder.adjust(1)
    
    return builder.as_markup()



def get_teacher_requests_keyboard(teacher_id: int):
    """Клавиатура заявок для преподавателя"""
    builder = InlineKeyboardBuilder()
    
    builder.add(InlineKeyboardButton(text="🎫 Мои заявки", callback_data=f"teacher_requests:{teacher_id}"))
    builder.add(InlineKeyboardButton(text="📚 По направлениям", callback_data=f"teacher_directions:{teacher_id}"))
    builder.add(InlineKeyboardButton(text="📊 Статистика", callback_data=f"teacher_stats:{teacher_id}"))
    
    builder.adjust(1)
    return builder.as_markup()

def get_statistics_keyboard(chat_type: ChatType):
    """Клавиатура статистики в зависимости от типа чата"""
    builder = InlineKeyboardBuilder()
    
    if chat_type in [ChatType.PRIVATE_ADMIN, ChatType.ADMIN_GROUP]:
        builder.add(InlineKeyboardButton(text="📈 Общая статистика", callback_data="stats_general"))
        builder.add(InlineKeyboardButton(text="🎫 Статистика заявок", callback_data="stats_requests"))
        builder.add(InlineKeyboardButton(text="👥 Активность пользователей", callback_data="stats_users"))
        builder.add(InlineKeyboardButton(text="📚 По направлениям", callback_data="stats_directions"))
        builder.adjust(2, 2)
    
    elif chat_type == ChatType.PRIVATE_TEACHER:
        builder.add(InlineKeyboardButton(text="🎫 Мои заявки", callback_data="stats_my_requests"))
        builder.add(InlineKeyboardButton(text="📚 Мои направления", callback_data="stats_my_directions"))
        builder.adjust(2)
    
    return builder.as_markup()

def get_settings_keyboard(chat_type: ChatType):
    """Клавиатура настроек"""
    builder = InlineKeyboardBuilder()
    
    if chat_type == ChatType.PRIVATE_ADMIN:
        builder.add(InlineKeyboardButton(text="👥 Управление админами", callback_data="settings_admins"))
        builder.add(InlineKeyboardButton(text="👨‍🏫 Управление преподавателями", callback_data="settings_teachers"))
        builder.add(InlineKeyboardButton(text="📢 Настройка уведомлений", callback_data="settings_notifications"))
        builder.add(InlineKeyboardButton(text="🎫 Настройки заявок", callback_data="settings_requests"))
        builder.add(InlineKeyboardButton(text="📅 Настройки расписания", callback_data="settings_schedule"))
        builder.adjust(1)
    
    elif chat_type == ChatType.ADMIN_GROUP:
        builder.add(InlineKeyboardButton(text="🔔 Уведомления", callback_data="group_notifications"))
        builder.add(InlineKeyboardButton(text="🎫 Фильтры заявок", callback_data="group_filters"))
        builder.adjust(2)
    
    return builder.as_markup()

# Функции для получения кнопок быстрых действий

def get_quick_actions_for_request(request_id: int, chat_type: ChatType):
    """Кнопки быстрых действий для заявки"""
    builder = InlineKeyboardBuilder()
    
    builder.add(InlineKeyboardButton(text="💬 Ответить", callback_data=f"reply_request:{request_id}"))
    
    if chat_type in [ChatType.PRIVATE_ADMIN, ChatType.ADMIN_GROUP]:
        builder.add(InlineKeyboardButton(text="🔒 Закрыть", callback_data=f"close_request:{request_id}"))
        builder.add(InlineKeyboardButton(text="👤 Профиль пользователя", callback_data=f"user_profile:{request_id}"))
        builder.adjust(1)
    else:
        builder.adjust(1)
    
    return builder.as_markup()

def get_help_keyboard(chat_type: ChatType):
    """Клавиатура помощи"""
    builder = InlineKeyboardBuilder()
    
    if chat_type == ChatType.PRIVATE_USER:
        builder.add(InlineKeyboardButton(text="📅 Как посмотреть расписание?", callback_data="help_schedule"))
        builder.add(InlineKeyboardButton(text="💬 Как создать заявку?", callback_data="help_feedback"))
        builder.add(InlineKeyboardButton(text="🤖 О боте", callback_data="help_about"))
    
    elif chat_type == ChatType.PRIVATE_ADMIN:
        builder.add(InlineKeyboardButton(text="👥 Управление пользователями", callback_data="help_admin_users"))
        builder.add(InlineKeyboardButton(text="🎫 Работа с заявками", callback_data="help_admin_requests"))
        builder.add(InlineKeyboardButton(text="📊 Статистика", callback_data="help_admin_stats"))
        builder.add(InlineKeyboardButton(text="⚙️ Настройки", callback_data="help_admin_settings"))
    
    elif chat_type == ChatType.PRIVATE_TEACHER:
        builder.add(InlineKeyboardButton(text="🎫 Работа с заявками", callback_data="help_teacher_requests"))
        builder.add(InlineKeyboardButton(text="📚 Управление направлениями", callback_data="help_teacher_directions"))
    
    builder.adjust(1)
    return builder.as_markup()
