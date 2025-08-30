from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from schedule_parser import schedule_parser

def get_main_keyboard():
    """Главная клавиатура"""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="📅 Расписание"))
    builder.add(KeyboardButton(text="💬 Обратная связь"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

# Старая функция get_admin_keyboard удалена - используется get_admin_keyboard из enhanced_keyboards.py

def get_schedule_directions_keyboard():
    """Клавиатура с направлениями"""
    directions = schedule_parser.get_directions()
    
    if not directions:
        return InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="❌ Расписание недоступно", callback_data="no_schedule")
        ]])
    
    builder = InlineKeyboardBuilder()
    
    for idx, direction in enumerate(directions):
        # Обрезаем длинные названия для кнопок
        button_text = direction[:45] + "..." if len(direction) > 45 else direction
        builder.add(InlineKeyboardButton(
            text=button_text,
            callback_data=f"dir:{idx}"  # Используем короткий индекс
        ))
    
    builder.adjust(1)  # По одной кнопке в ряд
    return builder.as_markup()

def get_direction_days_keyboard(direction_idx: int):
    """Клавиатура с днями для направления"""
    directions = schedule_parser.get_directions()
    if direction_idx >= len(directions):
        return InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="❌ Направление не найдено", callback_data="no_direction")
        ]])
    
    direction = directions[direction_idx]
    days = schedule_parser.get_days_for_direction(direction)
    
    if not days:
        return InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="❌ Нет занятий", callback_data="no_classes")
        ]])
    
    builder = InlineKeyboardBuilder()
    
    # Добавляем кнопку для показа всего расписания
    builder.add(InlineKeyboardButton(
        text="📋 Полное расписание",
        callback_data=f"full:{direction_idx}"
    ))
    
    # Добавляем кнопки для каждого дня
    day_mapping = {
        'Понедельник': 'пн', 'Вторник': 'вт', 'Среда': 'ср', 
        'Четверг': 'чт', 'Пятница': 'пт', 'Суббота': 'сб'
    }
    
    for day in days:
        short_day = day_mapping.get(day, day[:2])
        builder.add(InlineKeyboardButton(
            text=day,
            callback_data=f"day:{direction_idx}:{short_day}"
        ))
    
    # Кнопка назад
    builder.add(InlineKeyboardButton(
        text="⬅️ Назад к направлениям",
        callback_data="back_to_directions"
    ))
    
    builder.adjust(1)  # По одной кнопке в ряд
    return builder.as_markup()

def get_back_to_directions_keyboard():
    """Клавиатура с кнопкой назад к направлениям"""
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="⬅️ Назад к направлениям", callback_data="back_to_directions")
    ]])

def get_schedule_directions_keyboard_for_groups():
    """Клавиатура с направлениями для групп (с кнопкой назад в меню)"""
    directions = schedule_parser.get_directions()
    
    if not directions:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Расписание недоступно", callback_data="no_schedule")],
            [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_group_menu")]
        ])
    
    builder = InlineKeyboardBuilder()
    
    for idx, direction in enumerate(directions):
        # Обрезаем длинные названия для кнопок
        button_text = direction[:45] + "..." if len(direction) > 45 else direction
        builder.add(InlineKeyboardButton(
            text=button_text,
            callback_data=f"dir:{idx}"  # Используем короткий индекс
        ))
    
    # Добавляем кнопку "Назад в меню"
    builder.add(InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_group_menu"))
    
    builder.adjust(1)  # По одной кнопке в ряд
    return builder.as_markup()

def get_back_to_directions_keyboard_for_groups():
    """Клавиатура с кнопкой назад к направлениям для групп"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад к направлениям", callback_data="back_to_directions")],
        [InlineKeyboardButton(text="🏠 Назад в меню", callback_data="back_to_group_menu")]
    ])

def get_admin_management_keyboard():
    """Клавиатура управления администраторами"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="➕ Добавить админа", callback_data="add_admin"))
    builder.add(InlineKeyboardButton(text="➖ Удалить админа", callback_data="remove_admin"))
    builder.add(InlineKeyboardButton(text="📋 Список админов", callback_data="list_admins"))
    builder.add(InlineKeyboardButton(text="🔄 Обновить информацию", callback_data="update_admins_info"))
    builder.add(InlineKeyboardButton(text="⬅️ Назад к настройкам", callback_data="back_to_settings"))
    builder.adjust(1)
    return builder.as_markup()

def get_directions_keyboard(directions):
    """Клавиатура с направлениями для создания заявки"""
    builder = InlineKeyboardBuilder()
    
    # Добавляем специальную кнопку "Администрация"
    builder.add(InlineKeyboardButton(
        text="👑 Администрация",
        callback_data="select_direction:admin"
    ))
    
    for direction_id, direction_name in directions:
        # Обрезаем длинные названия для кнопок
        button_text = direction_name[:45] + "..." if len(direction_name) > 45 else direction_name
        builder.add(InlineKeyboardButton(
            text=button_text,
            callback_data=f"select_direction:{direction_id}"
        ))
    
    builder.add(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_feedback"))
    builder.adjust(1)
    return builder.as_markup()

def get_teacher_management_keyboard():
    """Клавиатура управления преподавателями"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="➕ Добавить преподавателя", callback_data="add_teacher"))
    builder.add(InlineKeyboardButton(text="➖ Удалить преподавателя", callback_data="remove_teacher"))
    builder.add(InlineKeyboardButton(text="📋 Список преподавателей", callback_data="list_teachers"))
    builder.add(InlineKeyboardButton(text="🔗 Привязки к направлениям", callback_data="teacher_directions"))
    builder.add(InlineKeyboardButton(text="⬅️ Назад к настройкам", callback_data="back_to_settings"))
    builder.adjust(1)
    return builder.as_markup()

def get_back_to_teacher_management_keyboard():
    """Клавиатура с кнопкой назад к управлению преподавателями"""
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="⬅️ Назад к преподавателям", callback_data="settings_teachers")
    ]])

def get_directions_list_keyboard(directions):
    """Клавиатура со списком направлений для привязки"""
    builder = InlineKeyboardBuilder()
    
    for direction_id, direction_name in directions:
        button_text = direction_name[:40] + "..." if len(direction_name) > 40 else direction_name
        builder.add(InlineKeyboardButton(
            text=button_text,
            callback_data=f"manage_direction:{direction_id}"
        ))
    
    builder.add(InlineKeyboardButton(text="⬅️ Назад к преподавателям", callback_data="settings_teachers"))
    builder.adjust(1)
    return builder.as_markup()

def get_direction_teachers_keyboard(direction_id, teachers, all_teachers):
    """Клавиатура для управления преподавателями направления"""
    builder = InlineKeyboardBuilder()
    
    assigned_teacher_ids = [t[0] for t in teachers]
    
    # Показываем назначенных преподавателей
    if teachers:
        for teacher_id, username, first_name in teachers:
            display_name = f"@{username}" if username else f"ID{teacher_id}"
            builder.add(InlineKeyboardButton(
                text=f"❌ {display_name}",
                callback_data=f"unassign_teacher:{direction_id}:{teacher_id}"
            ))
    
    # Показываем доступных для назначения преподавателей
    available_teachers = [t for t in all_teachers if t[0] not in assigned_teacher_ids]
    if available_teachers:
        for teacher_id, username, first_name in available_teachers:
            display_name = f"@{username}" if username else f"ID{teacher_id}"
            builder.add(InlineKeyboardButton(
                text=f"➕ {display_name}",
                callback_data=f"assign_teacher:{direction_id}:{teacher_id}"
            ))
    
    builder.add(InlineKeyboardButton(text="⬅️ Назад к направлениям", callback_data="teacher_directions"))
    builder.adjust(1)
    return builder.as_markup()

def get_cancel_keyboard():
    """Клавиатура отмены"""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True
    )

def get_cancel_inline_keyboard():
    """Inline клавиатура отмены"""
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_feedback")
    ]])

def get_send_feedback_keyboard():
    """Клавиатура для отправки заявки с прикреплениями"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Отправить заявку", callback_data="send_feedback")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_feedback")]
    ])

def get_back_to_admin_management_keyboard():
    """Клавиатура с кнопкой назад к управлению админами"""
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="⬅️ Назад к управлению", callback_data="back_to_admin_management")
    ]])

def get_notification_settings_keyboard():
    """Клавиатура настройки уведомлений"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="➕ Добавить чат", callback_data="add_notification_chat"))
    builder.add(InlineKeyboardButton(text="📋 Список чатов", callback_data="list_notification_chats"))
    builder.add(InlineKeyboardButton(text="⬅️ Назад к настройкам", callback_data="back_to_settings"))
    builder.adjust(1)
    return builder.as_markup()

def get_back_to_notification_settings_keyboard():
    """Клавиатура с кнопкой назад к настройкам уведомлений"""
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="⬅️ Назад к настройкам", callback_data="settings_notifications")
    ]])

def get_notification_chat_actions_keyboard(chat_id: int, is_active: bool):
    """Клавиатура действий с чатом уведомлений"""
    builder = InlineKeyboardBuilder()
    
    # Кнопка включить/отключить
    if is_active:
        builder.add(InlineKeyboardButton(text="🔇 Отключить", callback_data=f"toggle_chat:{chat_id}:0"))
    else:
        builder.add(InlineKeyboardButton(text="🔔 Включить", callback_data=f"toggle_chat:{chat_id}:1"))
    
    # Кнопка удалить
    builder.add(InlineKeyboardButton(text="🗑 Удалить", callback_data=f"remove_chat:{chat_id}"))
    
    # Кнопка назад
    builder.add(InlineKeyboardButton(text="⬅️ Назад к списку", callback_data="list_notification_chats"))
    
    builder.adjust(2, 1, 1)
    return builder.as_markup()
