from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from api_client import OneDashAPIError, OneDashRateLimitError
from bot.context import AppContext
from bot.states import TopUpStates
from keyboards.common import back_keyboard, url_keyboard

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "menu:topup")
async def request_topup_amount(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(TopUpStates.enter_amount)
    await callback.message.edit_text(
        "Введите сумму пополнения числом от 1 до 1000000.",
        reply_markup=back_keyboard(),
    )
    await callback.answer()


@router.message(TopUpStates.enter_amount)
async def process_topup_amount(message: Message, state: FSMContext, app_context: AppContext) -> None:
    raw = (message.text or "").strip().replace(",", ".")
    try:
        amount = float(raw)
    except ValueError:
        await message.answer("Введите корректную сумму числом.")
        return
    if amount < 1 or amount > 1_000_000:
        await message.answer("Сумма должна быть от 1 до 1000000.")
        return

    try:
        response = await app_context.client.top_up_balance(amount)
    except OneDashRateLimitError as exc:
        await message.answer(f"Слишком много запросов. Повторите через {exc.retry_after or 'несколько'} сек.")
        return
    except OneDashAPIError as exc:
        logger.warning("Top-up failed: %s", exc.message)
        await message.answer(f"Не удалось создать ссылку на оплату: {exc.message}")
        return

    await state.clear()
    await message.answer(
        "💳 Ссылка на пополнение готова.",
        reply_markup=url_keyboard("Открыть оплату", response["url"]),
    )
