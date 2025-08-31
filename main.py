import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import BOT_TOKEN
from database import db
from handlers import router
from group_handlers import group_router
from admin_handlers import admin_router
from teacher_handlers import teacher_router
from schedule_handlers import schedule_router
from schedule_parser import schedule_parser
from user_logging_middleware import UserLoggingMiddleware

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Основная функция запуска бота"""
    # Инициализация базы данных
    await db.init_db()
    logger.info("База данных инициализирована")
    
    # Загрузка расписания
    schedule_parser.load_schedule()
    logger.info("Расписание загружено")
    
    # Синхронизация направлений с базой данных
    directions = schedule_parser.get_directions()
    if directions:
        await db.sync_directions(directions)
        logger.info(f"Синхронизировано {len(directions)} направлений")
    
    # Создание бота и диспетчера
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    dp = Dispatcher()
    
    # Подключаем middleware для логирования пользователей
    dp.message.middleware(UserLoggingMiddleware())
    dp.callback_query.middleware(UserLoggingMiddleware())
    
    # Подключаем роутеры в порядке приоритета
    dp.include_router(group_router)      # Групповые чаты (высокий приоритет)
    dp.include_router(admin_router)      # Админские функции
    dp.include_router(teacher_router)    # Преподавательские функции
    dp.include_router(schedule_router)   # Обработчики расписания
    dp.include_router(router)            # Основные хендлеры (низкий приоритет)
    
    # Запуск бота
    logger.info("Бот запускается...")
    try:
        # Включаем обработку обновлений об изменениях участников чата
        await dp.start_polling(
            bot, 
            allowed_updates=['message', 'callback_query', 'my_chat_member']
        )
    except KeyboardInterrupt:
        logger.info("Бот остановлен")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
