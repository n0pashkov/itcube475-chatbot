import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# Токен бота из переменных окружения
BOT_TOKEN = os.getenv('BOT_TOKEN')

if not BOT_TOKEN:
    raise ValueError(
        "BOT_TOKEN не найден! "
        "Создайте файл .env с BOT_TOKEN=ваш_токен_бота или "
        "установите переменную окружения BOT_TOKEN"
    )

# ID первого администратора
FIRST_ADMIN_ID = 6038913790

# Настройки базы данных
DATABASE_PATH = 'bot_database.db'

# Настройки файлов
SCHEDULE_FILE = 'rasp.csv'
