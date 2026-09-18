from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from bot.context import AppContext


class AccessMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        app_context: AppContext = data["app_context"]
        user = getattr(event, "from_user", None)
        if not user or user.id == app_context.settings.admin_user_id:
            return await handler(event, data)

        if isinstance(event, Message):
            await event.answer("Извините, бот доступен только авторизованному администратору.")
        elif isinstance(event, CallbackQuery):
            await event.answer("Доступ запрещён.", show_alert=True)
        return None
