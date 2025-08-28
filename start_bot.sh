#!/bin/bash

echo "🚀 Запуск IT-Cube Telegram Bot..."
echo "📍 Текущая директория: $(pwd)"
echo "🐍 Версия Python: $(python3 --version)"
echo ""

# Проверяем наличие необходимых файлов
if [ ! -f ".env" ]; then
    echo "❌ Файл .env не найден!"
    echo "💡 Создайте .env файл на основе env.example:"
    echo "   cp env.example .env"
    echo "   # Затем отредактируйте .env и добавьте ваш BOT_TOKEN"
    exit 1
fi

if [ ! -f "rasp.csv" ]; then
    echo "❌ Файл rasp.csv не найден!"
    exit 1
fi

echo "✅ Все необходимые файлы найдены"
echo "🤖 Запускаем бота..."
echo ""

python3 main.py



