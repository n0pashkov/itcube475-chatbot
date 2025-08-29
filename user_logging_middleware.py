"""
Middleware для автоматического логирования всех пользователей, которые пишут боту
"""
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from database import db


class UserLoggingMiddleware(BaseMiddleware):
    """Middleware для логирования всех пользователей"""
    
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        """
        Обрабатывает каждое сообщение/callback и логирует пользователя
        """
        # Получаем информацию о пользователе
        user = event.from_user
        if user:
            # Логируем взаимодействие пользователя
            await db.log_user_interaction(
                user_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name
            )
        
        # Продолжаем обработку события
        return await handler(event, data)

