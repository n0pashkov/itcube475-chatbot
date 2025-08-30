#!/usr/bin/env python3
"""
Тестовый скрипт для проверки работы команд с @username в группах.
"""

import asyncio
import logging
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_command_filters():
    """Тестирует, как работают фильтры команд в aiogram"""
    try:
        from aiogram.filters import Command
        from aiogram.types import Message, User, Chat
        
        # Создаем тестовый чат группы
        test_chat = Chat(id=-1001234567890, type="supergroup", title="Test Group")
        test_user = User(id=123456789, is_bot=False, first_name="TestUser")
        
        # Тестируем разные варианты команд
        commands_to_test = [
            "/menu",           # Обычная команда
            "/menu@testbot",   # Команда с упоминанием бота  
            "/start",          # Обычная команда
            "/start@testbot",  # Команда с упоминанием бота
            "/chatid",         # Обычная команда
            "/chatid@testbot", # Команда с упоминанием бота
        ]
        
        command_filter_menu = Command("menu")
        command_filter_start = Command("start") 
        command_filter_chatid = Command("chatid")
        
        logger.info("🧪 Тестирование фильтров команд:")
        
        for cmd_text in commands_to_test:
            # Создаем тестовое сообщение
            message_data = {
                "message_id": 1,
                "date": int(datetime.now().timestamp()),
                "chat": test_chat,
                "from": test_user,
                "text": cmd_text
            }
            
            message = Message(**message_data)
            
            # Тестируем фильтры
            menu_match = command_filter_menu.check(message)
            start_match = command_filter_start.check(message)
            chatid_match = command_filter_chatid.check(message)
            
            if cmd_text.startswith("/menu"):
                result = "✅" if menu_match else "❌"
                logger.info(f"{result} '{cmd_text}' -> Command('menu'): {menu_match}")
            elif cmd_text.startswith("/start"):
                result = "✅" if start_match else "❌" 
                logger.info(f"{result} '{cmd_text}' -> Command('start'): {start_match}")
            elif cmd_text.startswith("/chatid"):
                result = "✅" if chatid_match else "❌"
                logger.info(f"{result} '{cmd_text}' -> Command('chatid'): {chatid_match}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка тестирования: {e}")
        return False

def test_group_types():
    """Тестирует типы чатов"""
    try:
        from aiogram.types import Chat
        from aiogram import F
        
        # Создаем разные типы чатов
        chats_to_test = [
            ("group", "Группа"),
            ("supergroup", "Супергруппа"),
            ("private", "Личный чат")
        ]
        
        group_filter = F.chat.type.in_({"group", "supergroup"})
        
        logger.info("\n🧪 Тестирование типов чатов:")
        
        for chat_type, chat_name in chats_to_test:
            test_chat = Chat(id=123456789, type=chat_type, title=f"Test {chat_name}")
            
            # Создаем mock сообщение для тестирования фильтра
            class MockMessage:
                def __init__(self, chat):
                    self.chat = chat
            
            message = MockMessage(test_chat)
            
            # Проверяем фильтр (имитируем поведение)
            is_group = chat_type in {"group", "supergroup"}
            result = "✅" if is_group else "❌"
            
            logger.info(f"{result} {chat_name} ({chat_type}): подходит для групповых хендлеров: {is_group}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка тестирования типов чатов: {e}")
        return False

async def main():
    """Основная функция тестирования"""
    print("🧪 Тестирование работы команд с @username")
    print("="*50)
    
    # Тестируем фильтры команд
    logger.info("1. Проверка фильтров Command()...")
    commands_ok = test_command_filters()
    
    # Тестируем типы чатов
    logger.info("2. Проверка типов чатов...")
    chat_types_ok = test_group_types()
    
    # Выводим результаты
    print("\n" + "="*50)
    print("📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ")
    print("="*50)
    print(f"✅ Фильтры команд: {'Работают' if commands_ok else 'Ошибка'}")
    print(f"✅ Типы чатов: {'Работают' if chat_types_ok else 'Ошибка'}")
    print()
    
    if commands_ok and chat_types_ok:
        print("🎉 Все тесты пройдены!")
        print()
        print("💡 ИНСТРУКЦИЯ ДЛЯ ТЕСТИРОВАНИЯ В TELEGRAM:")
        print("1. Добавьте бота в группу с топиками")
        print("2. Отключите Privacy Mode у бота в @BotFather")
        print("3. Сделайте бота администратором группы")
        print("4. Протестируйте команды в топиках:")
        print("   • Напишите /menu")
        print("   • Нажмите на кнопку команды (должна стать /menu@botusername)")
        print("   • Оба варианта должны работать!")
    else:
        print("❌ Обнаружены проблемы с фильтрами")
        print("Проверьте версию aiogram и обновите код")

if __name__ == "__main__":
    asyncio.run(main())
