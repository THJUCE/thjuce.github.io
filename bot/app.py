from __future__ import annotations

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

from api_client import OneDashClient
from bot.context import AppContext
from bot.middlewares.access import AccessMiddleware
from bot.middlewares.errors import ErrorMiddleware
from bot.services.cache import TTLCache
from bot.services.guards import OperationGuard
from config import Settings
from handlers import balance_router, create_router, servers_router, start_router, tariffs_router, topup_router


def create_dispatcher(settings: Settings) -> tuple[Bot, Dispatcher, AppContext]:
    bot = Bot(settings.telegram_bot_token, default=DefaultBotProperties(parse_mode="HTML"))
    dispatcher = Dispatcher()
    client = OneDashClient(base_url=settings.api_base_url, api_key=settings.onedash_api_key, timeout=settings.request_timeout)
    context = AppContext(
        settings=settings,
        client=client,
        cache=TTLCache(settings.cache_ttl_seconds),
        guard=OperationGuard(settings.debounce_ttl_seconds),
    )
    dispatcher.update.outer_middleware(ErrorMiddleware())
    dispatcher.update.middleware(AccessMiddleware())
    dispatcher["app_context"] = context
    dispatcher.include_router(start_router)
    dispatcher.include_router(balance_router)
    dispatcher.include_router(servers_router)
    dispatcher.include_router(create_router)
    dispatcher.include_router(tariffs_router)
    dispatcher.include_router(topup_router)
    return bot, dispatcher, context
