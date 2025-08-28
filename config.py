import os

# Токен бота из файла cred.txt
with open('cred.txt', 'r') as f:
    BOT_TOKEN = f.readline().strip()

# ID первого администратора
FIRST_ADMIN_ID = 6038913790

# Настройки базы данных
DATABASE_PATH = 'bot_database.db'

# Настройки файлов
SCHEDULE_FILE = 'rasp.csv'
