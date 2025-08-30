#!/usr/bin/env python3
"""
Простой скрипт для тестирования работы бота в топиках.
Этот скрипт поможет проверить, правильно ли бот обрабатывает топики.
"""

import asyncio
import logging
from datetime import datetime

# Настройка логирования для тестирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_message_thread_support():
    """Проверяет, поддерживает ли aiogram message_thread_id"""
    try:
        from aiogram.types import Message
        
        # Создаем тестовое сообщение
        test_data = {
            "message_id": 1,
            "date": int(datetime.now().timestamp()),
            "chat": {"id": -1001234567890, "type": "supergroup"},
            "from": {"id": 123456789, "is_bot": False, "first_name": "Test"},
            "text": "/menu",
            "message_thread_id": 42  # ID топика
        }
        
        message = Message(**test_data)
        
        # Проверяем наличие атрибута message_thread_id
        has_thread_id = hasattr(message, 'message_thread_id')
        thread_id_value = getattr(message, 'message_thread_id', None)
        
        logger.info(f"✅ Message.message_thread_id поддерживается: {has_thread_id}")
        logger.info(f"✅ Значение message_thread_id: {thread_id_value}")
        
        return has_thread_id and thread_id_value == 42
        
    except Exception as e:
        logger.error(f"❌ Ошибка проверки поддержки топиков: {e}")
        return False

def test_thread_id_extraction():
    """Тестирует извлечение message_thread_id как в коде бота"""
    try:
        from aiogram.types import Message
        
        # Тестируем с топиком
        test_data_with_topic = {
            "message_id": 1,
            "date": int(datetime.now().timestamp()),
            "chat": {"id": -1001234567890, "type": "supergroup"},
            "from": {"id": 123456789, "is_bot": False, "first_name": "Test"},
            "text": "/menu",
            "message_thread_id": 42
        }
        
        # Тестируем без топика
        test_data_without_topic = {
            "message_id": 2,
            "date": int(datetime.now().timestamp()),
            "chat": {"id": -1001234567890, "type": "supergroup"},
            "from": {"id": 123456789, "is_bot": False, "first_name": "Test"},
            "text": "/menu"
        }
        
        message_with_topic = Message(**test_data_with_topic)
        message_without_topic = Message(**test_data_without_topic)
        
        # Тестируем нашу логику извлечения
        thread_id_1 = getattr(message_with_topic, 'message_thread_id', None)
        thread_id_2 = getattr(message_without_topic, 'message_thread_id', None)
        
        logger.info(f"✅ Сообщение с топиком - thread_id: {thread_id_1}")
        logger.info(f"✅ Сообщение без топика - thread_id: {thread_id_2}")
        
        # Проверяем корректность
        success = (thread_id_1 == 42) and (thread_id_2 is None)
        
        if success:
            logger.info("✅ Логика извлечения message_thread_id работает корректно!")
        else:
            logger.error("❌ Ошибка в логике извлечения message_thread_id")
            
        return success
        
    except Exception as e:
        logger.error(f"❌ Ошибка тестирования извлечения thread_id: {e}")
        return False

def check_bot_files():
    """Проверяет, что файлы бота обновлены для поддержки топиков"""
    import os
    
    files_to_check = [
        'group_handlers.py',
        'handlers.py',
        'TOPICS_SETUP_GUIDE.md'
    ]
    
    for filename in files_to_check:
        if os.path.exists(filename):
            logger.info(f"✅ Файл {filename} найден")
            
            # Проверяем содержимое на наличие поддержки топиков
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()
                
            if 'message_thread_id' in content:
                logger.info(f"✅ В файле {filename} найдена поддержка топиков")
            else:
                logger.warning(f"⚠️ В файле {filename} не найдена поддержка топиков")
        else:
            logger.error(f"❌ Файл {filename} не найден")

def print_setup_reminder():
    """Выводит напоминание о настройке бота"""
    print("\n" + "="*60)
    print("🔧 НАПОМИНАНИЕ О НАСТРОЙКЕ БОТА ДЛЯ ТОПИКОВ")
    print("="*60)
    print()
    print("Для работы бота в топиках необходимо:")
    print()
    print("1. 🤖 Отключить Privacy Mode у бота:")
    print("   • Откройте @BotFather")
    print("   • /mybots → выберите бота → Bot Settings → Group Privacy → Turn off")
    print()
    print("2. 👑 Сделать бота администратором группы (рекомендуется)")
    print()
    print("3. 🔄 Удалить и заново добавить бота в группу")
    print()
    print("4. 🧪 Протестировать команды в топиках:")
    print("   • /start")
    print("   • /menu") 
    print("   • /chatid")
    print()
    print("📖 Подробная инструкция: TOPICS_SETUP_GUIDE.md")
    print("="*60)

async def main():
    """Основная функция тестирования"""
    print("🧪 Тестирование поддержки топиков в IT-Cube Bot")
    print("="*50)
    
    # Проверяем поддержку message_thread_id
    logger.info("1. Проверка поддержки message_thread_id в aiogram...")
    thread_support = check_message_thread_support()
    
    # Тестируем логику извлечения
    logger.info("2. Тестирование логики извлечения thread_id...")
    extraction_test = test_thread_id_extraction()
    
    # Проверяем файлы
    logger.info("3. Проверка обновленных файлов...")
    check_bot_files()
    
    # Выводим результаты
    print("\n" + "="*50)
    print("📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ")
    print("="*50)
    print(f"✅ Поддержка топиков в aiogram: {'Да' if thread_support else 'Нет'}")
    print(f"✅ Логика извлечения thread_id: {'Работает' if extraction_test else 'Ошибка'}")
    print()
    
    if thread_support and extraction_test:
        print("🎉 Код бота готов для работы с топиками!")
        print_setup_reminder()
    else:
        print("❌ Обнаружены проблемы с поддержкой топиков")
        print("Проверьте версию aiogram и обновите код")

if __name__ == "__main__":
    asyncio.run(main())
