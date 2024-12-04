import logging
import asyncio
from typing import List, Union, Callable, Any, Awaitable

from aiogram import types

from aiogram import types
from aiogram import BaseMiddleware
from aiogram.dispatcher.event.bases import CancelHandler
from aiogram.types import Message


class LoggingMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        # Проверяем, что событие является сообщением
        if isinstance(event, types.Message | types.CallbackQuery):
            # Логируем событие
            logging.info(f"Event from {event.from_user.id}: {event}")

        # Вызываем следующий обработчик в цепочке
        await handler(event, data)
