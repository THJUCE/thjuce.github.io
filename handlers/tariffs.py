from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from api_client import OneDashAPIError
from bot.context import AppContext
from bot.formatters import format_tariff_text
from bot.services.catalog import get_locations, get_tariffs
from keyboards.common import back_keyboard

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "menu:tariffs")
async def tariffs_menu(callback: CallbackQuery, app_context: AppContext) -> None:
    try:
        locations = await get_locations(app_context)
    except OneDashAPIError as exc:
        await callback.message.edit_text(f"Не удалось загрузить тарифы: {exc.message}", reply_markup=back_keyboard())
        await callback.answer()
        return

    builder = InlineKeyboardBuilder()
    for item in locations:
        location = item.get("location")
        for processor in item.get("processors", []):
            builder.button(
                text=f"{location.upper()} / {processor}",
                callback_data=f"tariffs:combo:{location}:{processor}",
            )
    builder.button(text="⬅️ Назад", callback_data="menu:root")
    builder.adjust(1)
    await callback.message.edit_text("Выберите локацию и процессор для просмотра тарифов:", reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("tariffs:combo:"))
async def tariffs_for_combo(callback: CallbackQuery, app_context: AppContext) -> None:
    _, _, location, processor = callback.data.split(":", 3)
    try:
        data = await get_tariffs(app_context, location=location, processor=processor)
    except OneDashAPIError as exc:
        logger.warning("Tariffs fetch failed: %s", exc.message)
        text = f"Не удалось получить тарифы: {exc.message}"
    else:
        items = data.get("items", [])
        currency = data.get("currency", "RUB")
        if not items:
            text = "Тарифы для выбранной комбинации не найдены."
        else:
            lines = [f"📋 <b>Тарифы {location.upper()} / {processor}</b>"]
            lines.extend(format_tariff_text(item, currency) for item in items)
            text = "\n\n".join(lines)
    await callback.message.edit_text(text, reply_markup=back_keyboard("menu:tariffs"), parse_mode="HTML")
    await callback.answer()
