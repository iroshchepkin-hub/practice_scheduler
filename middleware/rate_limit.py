
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from typing import Dict, Any, Callable, Awaitable
import time
from collections import defaultdict
from config import config


class RateLimitMiddleware(BaseMiddleware):
    """Middleware для ограничения запросов"""

    def __init__(self):
        self.requests = defaultdict(list)
        self.limit = config.MAX_REQUESTS_PER_MINUTE
        self.window = 60  # 1 минута

    async def __call__(
            self,
            handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
            event: Message | CallbackQuery,
            data: Dict[str, Any]
    ) -> Any:
        user_id = event.from_user.id
        current_time = time.time()

        # Очистка старых запросов
        self.requests[user_id] = [
            req_time for req_time in self.requests[user_id]
            if current_time - req_time < self.window
        ]

        # Проверка лимита
        if len(self.requests[user_id]) >= self.limit:
            if isinstance(event, Message):
                await event.answer(
                    "⚠️ <b>Слишком много запросов</b>\n"
                    "Пожалуйста, подождите 1 минуту.",
                    parse_mode="HTML"
                )
            return

        # Добавляем запрос
        self.requests[user_id].append(current_time)

        return await handler(event, data)