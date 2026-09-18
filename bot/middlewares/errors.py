from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

logger = logging.getLogger(__name__)


class ErrorMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        try:
            return await handler(event, data)
        except Exception:
            logger.exception("Unhandled bot error")
            if isinstance(event, Message):
                await event.answer("Произошла ошибка, попробуйте позже.")
            elif isinstance(event, CallbackQuery):
                await event.answer("Произошла ошибка, попробуйте позже.", show_alert=True)
            return None
