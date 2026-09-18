from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery

from api_client import OneDashAPIError, OneDashRateLimitError
from bot.context import AppContext
from bot.formatters import format_money
from keyboards.common import back_keyboard

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "menu:balance")
async def show_balance(callback: CallbackQuery, app_context: AppContext) -> None:
    try:
        data = (await app_context.client.balance()).get("data", {})
    except OneDashRateLimitError as exc:
        text = f"OneDash временно ограничил запросы. Повторите через {exc.retry_after or 'несколько'} сек."
    except OneDashAPIError as exc:
        logger.warning("Balance request failed: %s", exc.message)
        text = f"Не удалось получить баланс: {exc.message}"
    else:
        text = (
            "📊 <b>Баланс аккаунта</b>\n"
            f"Сумма: {format_money(data.get('balance'), data.get('currency'))}\n"
            f"Локаль: {data.get('locale', '—')}"
        )
    await callback.message.edit_text(text, reply_markup=back_keyboard(), parse_mode="HTML")
    await callback.answer()
