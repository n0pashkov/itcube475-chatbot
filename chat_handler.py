"""
Модуль для обработки разных типов чатов и определения поведения бота
"""
from enum import Enum
from typing import Optional, Dict, Any
from aiogram.types import Message, CallbackQuery
from database import db

class ChatType(Enum):
    """Типы чатов для разного поведения бота"""
    PRIVATE_USER = "private_user"           # Личный чат с обычным пользователем
    PRIVATE_ADMIN = "private_admin"         # Личный чат с администратором  
    PRIVATE_TEACHER = "private_teacher"     # Личный чат с преподавателем
    PUBLIC_GROUP = "public_group"          # Обычная группа/супергруппа
    ADMIN_GROUP = "admin_group"            # Админская группа (для уведомлений)
    TEACHER_GROUP = "teacher_group"        # Преподавательская группа

class ChatBehavior:
    """Класс для определения поведения бота в разных типах чатов"""
    
    @staticmethod
    async def determine_chat_type(message: Message) -> ChatType:
        """Определить тип чата и роль пользователя"""
        chat = message.chat
        user_id = message.from_user.id
        
        # Личные чаты
        if chat.type == 'private':
            is_admin = await db.is_admin(user_id)
            is_teacher = await db.is_teacher(user_id)
            
            if is_admin:
                return ChatType.PRIVATE_ADMIN
            elif is_teacher:
                return ChatType.PRIVATE_TEACHER
            else:
                return ChatType.PRIVATE_USER
        
        # Групповые чаты
        elif chat.type in ['group', 'supergroup']:
            # Проверяем, является ли группа админской (настроена для уведомлений)
            if await db.is_notification_chat(chat.id):
                return ChatType.ADMIN_GROUP
            
            # Можно добавить логику для определения преподавательских групп
            # Например, по названию группы или специальной настройке
            if await ChatBehavior._is_teacher_group(chat.id):
                return ChatType.TEACHER_GROUP
            
            return ChatType.PUBLIC_GROUP
        
        # По умолчанию - публичная группа
        return ChatType.PUBLIC_GROUP
    
    @staticmethod
    async def _is_teacher_group(chat_id: int) -> bool:
        """Проверить, является ли группа преподавательской"""
        # Здесь можно добавить логику определения преподавательских групп
        # Например, через специальную таблицу в БД или по паттерну в названии
        return False
    
    @staticmethod
    def get_allowed_commands(chat_type: ChatType) -> Dict[str, bool]:
        """Получить список разрешенных команд для типа чата"""
        commands = {
            # Базовые команды
            'start': True,
            'help': True,
            'chatid': True,
            
            # Пользовательские функции
            'schedule': False,
            'feedback': False,
            
            # Админские функции
            'admin_management': False,
            'teacher_management': False,
            'notification_settings': False,
            'view_requests': False,
            'statistics': False,
            
            # Преподавательские функции
            'my_requests': False,
            'reply_to_request': False,
            
            # Групповые функции
            'group_info': False,
            'quick_schedule': False,
        }
        
        if chat_type == ChatType.PRIVATE_USER:
            commands.update({
                'schedule': True,
                'feedback': True,
            })
        
        elif chat_type == ChatType.PRIVATE_ADMIN:
            commands.update({
                'schedule': True,
                'feedback': True,
                'admin_management': True,
                'teacher_management': True,
                'notification_settings': True,
                'view_requests': True,
                'statistics': True,
                'reply_to_request': True,
            })
        
        elif chat_type == ChatType.PRIVATE_TEACHER:
            commands.update({
                'schedule': True,
                'feedback': True,
                'my_requests': True,
                'reply_to_request': True,
            })
        
        elif chat_type == ChatType.PUBLIC_GROUP:
            commands.update({
                'group_info': True,
                'quick_schedule': True,
            })
        
        elif chat_type == ChatType.ADMIN_GROUP:
            commands.update({
                'group_info': True,
                'quick_schedule': True,
                'reply_to_request': True,
                'statistics': True,
            })
        
        elif chat_type == ChatType.TEACHER_GROUP:
            commands.update({
                'group_info': True,
                'quick_schedule': True,
                'reply_to_request': True,
            })
        
        return commands
    
    @staticmethod
    def get_welcome_message(chat_type: ChatType, user_name: str = "пользователь", chat_title: str = None) -> str:
        """Получить приветственное сообщение для типа чата"""
        
        if chat_type == ChatType.PRIVATE_USER:
            return (
                f"👋 Добро пожаловать, {user_name}!\n\n"
                "🤖 Это бот IT-Cube для работы с расписанием и обратной связью.\n\n"
                "📅 *Расписание* - просмотр расписания занятий по направлениям\n"
                "💬 *Обратная связь* - отправка сообщений администраторам"
            )
        
        elif chat_type == ChatType.PRIVATE_ADMIN:
            return (
                f"👋 Добро пожаловать, {user_name}!\n\n"
                "🤖 Это бот IT-Cube для работы с расписанием и обратной связью.\n\n"
                "📅 *Расписание* - просмотр расписания занятий по направлениям\n"
                "💬 *Обратная связь* - отправка сообщений администраторам\n\n"
                "👑 *Вы администратор!* У вас есть дополнительные возможности:\n"
                "• Управление администраторами и преподавателями\n"
                "• Настройка уведомлений\n"
                "• Просмотр и ответы на заявки\n"
                "• Статистика использования бота"
            )
        
        elif chat_type == ChatType.PRIVATE_TEACHER:
            return (
                f"👋 Добро пожаловать, {user_name}!\n\n"
                "🤖 Это бот IT-Cube для работы с расписанием и обратной связью.\n\n"
                "📅 *Расписание* - просмотр расписания занятий по направлениям\n"
                "💬 *Обратная связь* - отправка сообщений администраторам\n\n"
                "👨‍🏫 *Вы преподаватель!* Дополнительные возможности:\n"
                "• Просмотр заявок по вашим направлениям\n"
                "• Ответы на вопросы студентов\n"
                "• Быстрый доступ к расписанию ваших занятий"
            )
        
        elif chat_type == ChatType.PUBLIC_GROUP:
            return (
                f"👋 Привет! Я бот IT-Cube!\n\n"
                f"📋 *Группа:* {chat_title or 'Без названия'}\n\n"
                "🤖 Основные функции:\n"
                "• 📅 Быстрый просмотр расписания\n"
                "• 🆔 Получение ID чата\n"
                "• 💡 Информация о боте\n\n"
                "💬 Для полного функционала напишите мне в личные сообщения!"
            )
        
        elif chat_type == ChatType.ADMIN_GROUP:
            return (
                f"👋 Привет! Я бот IT-Cube!\n\n"
                f"📋 *Админская группа:* {chat_title or 'Без названия'}\n\n"
                "👑 *Админские функции:*\n"
                "• 🎫 Получение уведомлений о заявках\n"
                "• 💬 Быстрые ответы на обращения\n"
                "• 📊 Просмотр статистики\n"
                "• 📅 Управление расписанием\n\n"
                "🔔 Уведомления об обратной связи будут приходить в этот чат."
            )
        
        elif chat_type == ChatType.TEACHER_GROUP:
            return (
                f"👋 Привет! Я бот IT-Cube!\n\n"
                f"📋 *Преподавательская группа:* {chat_title or 'Без названия'}\n\n"
                "👨‍🏫 *Преподавательские функции:*\n"
                "• 🎫 Уведомления о заявках по направлениям\n"
                "• 💬 Ответы на вопросы студентов\n"
                "• 📅 Расписание занятий\n"
                "• 📝 Обратная связь от студентов\n\n"
                "📚 Здесь вы будете получать уведомления по вашим направлениям."
            )
        
        return "👋 Добро пожаловать!"
    
    @staticmethod
    async def can_execute_command(message: Message, command: str) -> bool:
        """Проверить, может ли пользователь выполнить команду в данном чате"""
        chat_type = await ChatBehavior.determine_chat_type(message)
        allowed_commands = ChatBehavior.get_allowed_commands(chat_type)
        return allowed_commands.get(command, False)
    
    @staticmethod
    async def get_restricted_message(chat_type: ChatType, command: str) -> str:
        """Получить сообщение об ограничении доступа к команде"""
        if chat_type in [ChatType.PUBLIC_GROUP, ChatType.ADMIN_GROUP, ChatType.TEACHER_GROUP]:
            return (
                f"⚠️ Команда '{command}' недоступна в групповых чатах.\n"
                "💬 Напишите мне в личные сообщения для доступа ко всем функциям!"
            )
        
        elif chat_type == ChatType.PRIVATE_USER:
            return (
                f"❌ У вас нет прав для выполнения команды '{command}'.\n"
                "Обратитесь к администратору для получения дополнительных прав."
            )
        
        return "❌ Команда недоступна в данном контексте."

# Декоратор для проверки прав доступа
def require_chat_type(*allowed_types: ChatType):
    """Декоратор для ограничения доступа к хендлерам по типу чата"""
    def decorator(handler):
        async def wrapper(message: Message, *args, **kwargs):
            chat_type = await ChatBehavior.determine_chat_type(message)
            if chat_type not in allowed_types:
                restricted_msg = await ChatBehavior.get_restricted_message(chat_type, handler.__name__)
                await message.answer(restricted_msg)
                return
            return await handler(message, *args, **kwargs)
        return wrapper
    return decorator

def require_permission(command: str):
    """Декоратор для проверки разрешения на выполнение команды"""
    def decorator(handler):
        async def wrapper(message: Message, *args, **kwargs):
            if not await ChatBehavior.can_execute_command(message, command):
                chat_type = await ChatBehavior.determine_chat_type(message)
                restricted_msg = await ChatBehavior.get_restricted_message(chat_type, command)
                await message.answer(restricted_msg)
                return
            return await handler(message, *args, **kwargs)
        return wrapper
    return decorator
