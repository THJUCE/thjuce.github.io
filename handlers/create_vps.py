from __future__ import annotations

import logging
from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from api_client import OneDashAPIError
from bot.context import AppContext
from bot.formatters import extract_price_for_period, format_money, humanize_os_name
from bot.services.catalog import get_locations, get_systems, get_tariffs
from bot.services.guards import BusyOperationError
from bot.states import CreateVPSStates
from keyboards.common import back_keyboard, confirmation_keyboard

logger = logging.getLogger(__name__)
router = Router()
COMMON_PERIODS = [7, 30, 60, 90, 180, 360]


async def _render_location_step(callback: CallbackQuery, app_context: AppContext) -> None:
    locations = await get_locations(app_context)
    builder = InlineKeyboardBuilder()
    for item in locations:
        location = item["location"]
        for processor in item.get("processors", []):
            builder.button(text=f"{location.upper()} / {processor}", callback_data=f"create:location:{location}:{processor}")
    builder.button(text="⬅️ Назад", callback_data="menu:root")
    builder.adjust(1)
    await callback.message.edit_text("Выберите локацию и процессор:", reply_markup=builder.as_markup())


@router.callback_query(F.data == "menu:create")
async def start_create_vps(callback: CallbackQuery, state: FSMContext, app_context: AppContext) -> None:
    await state.set_state(CreateVPSStates.choose_location)
    await state.clear()
    await state.set_state(CreateVPSStates.choose_location)
    await _render_location_step(callback, app_context)
    await callback.answer()


@router.callback_query(CreateVPSStates.choose_location, F.data.startswith("create:location:"))
async def choose_location(callback: CallbackQuery, state: FSMContext, app_context: AppContext) -> None:
    _, _, location, processor = callback.data.split(":", 3)
    tariffs_data = await get_tariffs(app_context, location=location, processor=processor)
    tariffs = tariffs_data.get("items", [])
    if not tariffs:
        await callback.message.edit_text("Для выбранной комбинации тарифов нет.", reply_markup=back_keyboard("menu:create"))
        await callback.answer()
        return
    await state.update_data(location=location, processor=processor)
    await state.set_state(CreateVPSStates.choose_tariff)
    builder = InlineKeyboardBuilder()
    for tariff in tariffs:
        builder.button(text=f"{tariff.get('name')} (ID {tariff.get('id')})", callback_data=f"create:tariff:{tariff['id']}")
    builder.button(text="⬅️ Назад", callback_data="menu:create")
    builder.adjust(1)
    await callback.message.edit_text("Выберите тариф:", reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(CreateVPSStates.choose_tariff, F.data.startswith("create:tariff:"))
async def choose_tariff(callback: CallbackQuery, state: FSMContext, app_context: AppContext) -> None:
    tariff_id = int(callback.data.rsplit(":", 1)[-1])
    data = await state.get_data()
    tariffs_data = await get_tariffs(app_context, location=data["location"], processor=data["processor"])
    tariff = next((item for item in tariffs_data.get("items", []) if item.get("id") == tariff_id), None)
    systems = await get_systems(app_context)
    await state.update_data(tariff_id=tariff_id, tariff=tariff)
    await state.set_state(CreateVPSStates.choose_system)
    builder = InlineKeyboardBuilder()
    for system in systems:
        builder.button(text=system.get("name", system["code"]), callback_data=f"create:system:{system['code']}")
    builder.button(text="⬅️ Назад", callback_data="menu:create")
    builder.adjust(1)
    await callback.message.edit_text("Выберите операционную систему:", reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(CreateVPSStates.choose_system, F.data.startswith("create:system:"))
async def choose_system(callback: CallbackQuery, state: FSMContext) -> None:
    system_code = callback.data.rsplit(":", 1)[-1]
    await state.update_data(system=system_code)
    await state.set_state(CreateVPSStates.choose_period)
    builder = InlineKeyboardBuilder()
    for period in COMMON_PERIODS:
        builder.button(text=f"{period} дн.", callback_data=f"create:period:{period}")
    builder.button(text="✍️ Ввести вручную", callback_data="create:period:custom")
    builder.button(text="⬅️ Назад", callback_data="menu:create")
    builder.adjust(2, 2, 2, 1)
    await callback.message.edit_text("Выберите срок аренды:", reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(CreateVPSStates.choose_period, F.data == "create:period:custom")
async def request_custom_period(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(CreateVPSStates.enter_custom_period)
    await callback.message.edit_text("Введите срок аренды числом от 7 до 360 дней.", reply_markup=back_keyboard("menu:create"))
    await callback.answer()


@router.message(CreateVPSStates.enter_custom_period)
async def process_custom_period(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    if not raw.isdigit():
        await message.answer("Введите срок числом от 7 до 360.")
        return
    period = int(raw)
    if period < 7 or period > 360:
        await message.answer("Срок должен быть от 7 до 360 дней.")
        return
    await state.update_data(period=period)
    await state.set_state(CreateVPSStates.choose_options)
    await message.answer("Настройте дополнительные опции:", reply_markup=_options_keyboard(await state.get_data()))


@router.callback_query(CreateVPSStates.choose_period, F.data.startswith("create:period:"))
async def choose_period(callback: CallbackQuery, state: FSMContext) -> None:
    period = int(callback.data.rsplit(":", 1)[-1])
    await state.update_data(period=period)
    await state.set_state(CreateVPSStates.choose_options)
    await callback.message.edit_text("Настройте дополнительные опции:", reply_markup=_options_keyboard(await state.get_data()))
    await callback.answer()


def _options_keyboard(data: dict[str, Any]):
    builder = InlineKeyboardBuilder()
    options = {
        "static_ip": "Static IP",
        "nvme": "NVMe",
        "backup": "Backup",
        "skip_desktop_link": "Без ярлыка OneDash",
    }
    system = data.get("system", "")
    for key, label in options.items():
        if key == "skip_desktop_link" and not str(system).startswith("windows"):
            continue
        enabled = bool(data.get(key, False))
        builder.button(text=f"{'✅' if enabled else '☑️'} {label}", callback_data=f"create:option:{key}")
    builder.button(text="Далее", callback_data="create:options:next")
    builder.button(text="⬅️ Назад", callback_data="menu:create")
    builder.adjust(1)
    return builder.as_markup()


@router.callback_query(CreateVPSStates.choose_options, F.data.startswith("create:option:"))
async def toggle_option(callback: CallbackQuery, state: FSMContext) -> None:
    key = callback.data.rsplit(":", 1)[-1]
    data = await state.get_data()
    await state.update_data(**{key: not bool(data.get(key, False))})
    await callback.message.edit_reply_markup(reply_markup=_options_keyboard(await state.get_data()))
    await callback.answer()


@router.callback_query(CreateVPSStates.choose_options, F.data == "create:options:next")
async def choose_count_step(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(CreateVPSStates.choose_count)
    builder = InlineKeyboardBuilder()
    for count in range(1, 11):
        builder.button(text=str(count), callback_data=f"create:count:{count}")
    builder.button(text="⬅️ Назад", callback_data="menu:create")
    builder.adjust(5, 5, 1)
    await callback.message.edit_text("Выберите количество VPS:", reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(CreateVPSStates.choose_count, F.data.startswith("create:count:"))
async def confirm_create_vps(callback: CallbackQuery, state: FSMContext, app_context: AppContext) -> None:
    count = int(callback.data.rsplit(":", 1)[-1])
    await state.update_data(count=count)
    await state.set_state(CreateVPSStates.confirm)
    data = await state.get_data()
    systems = await get_systems(app_context)
    tariff = data.get("tariff") or {}
    price_entry = extract_price_for_period(tariff, data["period"])
    currency = "RUB"
    total_price = None
    if price_entry:
        total_price = price_entry.get("price", 0) * count
        currency = (await get_tariffs(app_context, location=data["location"], processor=data["processor"])).get("currency", "RUB")
    options = [label for key, label in [("static_ip", "static IP"), ("nvme", "NVMe"), ("backup", "backup")] if data.get(key)]
    if data.get("skip_desktop_link"):
        options.append("без ярлыка OneDash")
    text = (
        "<b>Подтвердите создание VPS</b>\n"
        f"Локация: {data['location']} / {data['processor']}\n"
        f"Тариф: {tariff.get('name', data['tariff_id'])}\n"
        f"ОС: {humanize_os_name(data['system'], systems)}\n"
        f"Период: {data['period']} дн.\n"
        f"Количество: {count}\n"
        f"Опции: {', '.join(options) if options else 'нет'}\n"
        f"Итоговая стоимость: {format_money(total_price, currency) if total_price is not None else 'не указана в API'}"
    )
    await callback.message.edit_text(text, reply_markup=confirmation_keyboard("create:submit", "menu:create"), parse_mode="HTML")
    await callback.answer()


@router.callback_query(CreateVPSStates.confirm, F.data == "create:submit")
async def submit_create_vps(callback: CallbackQuery, state: FSMContext, app_context: AppContext) -> None:
    data = await state.get_data()
    key = f"create:{data['location']}:{data['processor']}:{data['tariff_id']}:{data['system']}:{data['period']}:{data['count']}"
    try:
        async with app_context.guard.lock(key):
            response = await app_context.client.create_vps(
                period=data["period"],
                tariff_id=data["tariff_id"],
                location=data["location"],
                processor=data["processor"],
                system=data["system"],
                count=data["count"],
                static_ip=bool(data.get("static_ip", False)),
                nvme=bool(data.get("nvme", False)),
                backup=bool(data.get("backup", False)),
                skip_desktop_link=bool(data.get("skip_desktop_link", False)),
            )
            await app_context.cache.invalidate("vps:")
    except BusyOperationError:
        await callback.answer("Запрос уже обрабатывается. Подождите пару секунд.", show_alert=True)
        return
    except OneDashAPIError as exc:
        logger.warning("Create VPS failed: %s", exc.message)
        await callback.message.edit_text(f"Не удалось создать VPS: {exc.message}", reply_markup=back_keyboard("menu:create"))
        await callback.answer()
        return
    await state.clear()
    await callback.message.edit_text(
        f"Создание VPS запущено. ID заказа: <code>{response.get('order_id', '—')}</code>.",
        reply_markup=back_keyboard("menu:servers"),
        parse_mode="HTML",
    )
    await callback.answer()
