from __future__ import annotations

import logging
from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from api_client import OneDashAPIError
from bot.context import AppContext
from bot.formatters import format_server_card, humanize_os_name
from bot.services.catalog import get_systems, get_tariffs, get_vps_items
from bot.states import CloneStates, ReinstallStates
from bot.services.guards import BusyOperationError
from keyboards.common import back_keyboard, confirmation_keyboard

logger = logging.getLogger(__name__)
router = Router()


def _find_vps(items: list[dict[str, Any]], vps_id: int) -> dict[str, Any] | None:
    for item in items:
        if item.get("id") == vps_id:
            return item
    return None


async def _show_server_detail(callback: CallbackQuery, app_context: AppContext, vps_id: int) -> None:
    items = await get_vps_items(app_context, force=True)
    systems = await get_systems(app_context)
    vps = _find_vps(items, vps_id)
    if not vps:
        await callback.message.edit_text("Сервер не найден.", reply_markup=back_keyboard("menu:servers"))
        return
    power = None
    try:
        power = (await app_context.client.power_status(vps_id=vps_id)).get("data", {})
    except OneDashAPIError:
        logger.info("Power status not available for VPS %s", vps_id)
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Перезагрузить", callback_data=f"server:reboot:{vps_id}")
    builder.button(text="♻️ Переустановить ОС", callback_data=f"server:reinstall:{vps_id}")
    builder.button(text="🔀 Сменить тариф", callback_data=f"server:tariff:{vps_id}")
    builder.button(text="📎 Клонировать", callback_data=f"server:clone:{vps_id}")
    builder.button(text="⬅️ Назад", callback_data="menu:servers")
    builder.adjust(2, 2, 1)
    await callback.message.edit_text(
        format_server_card(vps, systems, power),
        reply_markup=builder.as_markup(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "menu:servers")
async def list_servers(callback: CallbackQuery, app_context: AppContext) -> None:
    try:
        items = await get_vps_items(app_context, force=True)
    except OneDashAPIError as exc:
        await callback.message.edit_text(f"Не удалось загрузить серверы: {exc.message}", reply_markup=back_keyboard())
        await callback.answer()
        return
    builder = InlineKeyboardBuilder()
    if not items:
        builder.button(text="⬅️ Назад", callback_data="menu:root")
        await callback.message.edit_text("Серверы не найдены.", reply_markup=builder.as_markup())
        await callback.answer()
        return
    for item in items:
        host = item.get("connection", {}).get("host") or f"ID {item.get('id')}"
        builder.button(text=f"{host} · {item.get('id')}", callback_data=f"server:show:{item.get('id')}")
    builder.button(text="⬅️ Назад", callback_data="menu:root")
    builder.adjust(1)
    await callback.message.edit_text("🖥 <b>Мои серверы</b>", reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("server:show:"))
async def show_server(callback: CallbackQuery, app_context: AppContext) -> None:
    vps_id = int(callback.data.rsplit(":", 1)[-1])
    try:
        await _show_server_detail(callback, app_context, vps_id)
    except OneDashAPIError as exc:
        await callback.message.edit_text(f"Не удалось загрузить карточку сервера: {exc.message}", reply_markup=back_keyboard("menu:servers"))
    await callback.answer()


@router.callback_query(F.data.startswith("server:reboot:"))
async def confirm_reboot(callback: CallbackQuery) -> None:
    vps_id = int(callback.data.rsplit(":", 1)[-1])
    await callback.message.edit_text(
        f"Подтвердить перезагрузку VPS <code>{vps_id}</code>?",
        reply_markup=confirmation_keyboard(f"server:reboot:do:{vps_id}", f"server:show:{vps_id}"),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("server:reboot:do:"))
async def perform_reboot(callback: CallbackQuery, app_context: AppContext) -> None:
    vps_id = int(callback.data.rsplit(":", 1)[-1])
    try:
        async with app_context.guard.lock(f"reboot:{vps_id}"):
            response = await app_context.client.power_action(vps_id=vps_id, action="reboot")
            await app_context.cache.invalidate("vps:")
    except BusyOperationError:
        await callback.answer("Запрос уже обрабатывается. Подождите пару секунд.", show_alert=True)
        return
    except OneDashAPIError as exc:
        await callback.message.edit_text(f"Не удалось перезагрузить VPS: {exc.message}", reply_markup=back_keyboard(f"server:show:{vps_id}"))
        await callback.answer()
        return
    status = response.get("data", {}).get("power_action_status", "queued")
    await callback.message.edit_text(
        f"Перезагрузка VPS <code>{vps_id}</code> отправлена. Статус: {status}.",
        reply_markup=back_keyboard(f"server:show:{vps_id}"),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("server:reinstall:"))
async def start_reinstall(callback: CallbackQuery, state: FSMContext, app_context: AppContext) -> None:
    vps_id = int(callback.data.rsplit(":", 1)[-1])
    systems = await get_systems(app_context)
    await state.set_state(ReinstallStates.choose_system)
    await state.update_data(reinstall_vps_id=vps_id)
    builder = InlineKeyboardBuilder()
    for system in systems:
        builder.button(text=system.get("name", system["code"]), callback_data=f"reinstall:select:{system['code']}")
    builder.button(text="⬅️ Отмена", callback_data=f"server:show:{vps_id}")
    builder.adjust(1)
    await callback.message.edit_text("Выберите ОС для переустановки:", reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(ReinstallStates.choose_system, F.data.startswith("reinstall:select:"))
async def confirm_reinstall(callback: CallbackQuery, state: FSMContext, app_context: AppContext) -> None:
    system_code = callback.data.rsplit(":", 1)[-1]
    data = await state.get_data()
    vps_id = data["reinstall_vps_id"]
    systems = await get_systems(app_context)
    await state.set_state(ReinstallStates.confirm)
    await state.update_data(reinstall_system=system_code)
    await callback.message.edit_text(
        f"Переустановить VPS <code>{vps_id}</code> на {humanize_os_name(system_code, systems)}? Все данные будут удалены.",
        reply_markup=confirmation_keyboard(f"reinstall:do:{vps_id}:{system_code}", f"server:show:{vps_id}"),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("reinstall:do:"))
async def do_reinstall(callback: CallbackQuery, state: FSMContext, app_context: AppContext) -> None:
    _, _, vps_id_raw, system_code = callback.data.split(":", 3)
    vps_id = int(vps_id_raw)
    try:
        async with app_context.guard.lock(f"reinstall:{vps_id}"):
            await app_context.client.reinstall_vps(vps_id=vps_id, system=system_code)
            await app_context.cache.invalidate("vps:")
    except BusyOperationError:
        await callback.answer("Запрос уже обрабатывается. Подождите пару секунд.", show_alert=True)
        return
    except OneDashAPIError as exc:
        await callback.message.edit_text(f"Не удалось запустить переустановку: {exc.message}", reply_markup=back_keyboard(f"server:show:{vps_id}"))
        await callback.answer()
        return
    await state.clear()
    await callback.message.edit_text(
        f"Переустановка VPS <code>{vps_id}</code> запущена.",
        reply_markup=back_keyboard(f"server:show:{vps_id}"),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("server:tariff:"))
async def select_tariff(callback: CallbackQuery, app_context: AppContext) -> None:
    vps_id = int(callback.data.rsplit(":", 1)[-1])
    items = await get_vps_items(app_context, force=False)
    vps = _find_vps(items, vps_id)
    if not vps:
        await callback.message.edit_text("Сервер не найден.", reply_markup=back_keyboard("menu:servers"))
        await callback.answer()
        return
    data = await get_tariffs(app_context, location=vps["location"], processor=vps["processor"])
    builder = InlineKeyboardBuilder()
    for tariff in data.get("items", []):
        if tariff.get("id") == vps.get("tariff", {}).get("id"):
            continue
        builder.button(text=f"{tariff.get('name')} (ID {tariff.get('id')})", callback_data=f"tariff:confirm:{vps_id}:{vps['order_id']}:{tariff['id']}")
    builder.button(text="⬅️ Назад", callback_data=f"server:show:{vps_id}")
    builder.adjust(1)
    await callback.message.edit_text("Выберите новый тариф:", reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("tariff:confirm:"))
async def confirm_tariff_change(callback: CallbackQuery) -> None:
    _, _, vps_id_raw, order_id_raw, tariff_id_raw = callback.data.split(":", 4)
    vps_id = int(vps_id_raw)
    order_id = int(order_id_raw)
    tariff_id = int(tariff_id_raw)
    await callback.message.edit_text(
        f"Подтвердить смену тарифа заказа <code>{order_id}</code> на тариф ID <code>{tariff_id}</code>?",
        reply_markup=confirmation_keyboard(f"tariff:do:{vps_id}:{order_id}:{tariff_id}", f"server:show:{vps_id}"),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("tariff:do:"))
async def do_tariff_change(callback: CallbackQuery, app_context: AppContext) -> None:
    _, _, vps_id_raw, order_id_raw, tariff_id_raw = callback.data.split(":", 4)
    vps_id = int(vps_id_raw)
    order_id = int(order_id_raw)
    tariff_id = int(tariff_id_raw)
    try:
        async with app_context.guard.lock(f"tariff:{order_id}"):
            await app_context.client.change_order_tariff(order_id=order_id, tariff_id=tariff_id)
            await app_context.cache.invalidate("vps:")
    except BusyOperationError:
        await callback.answer("Запрос уже обрабатывается. Подождите пару секунд.", show_alert=True)
        return
    except OneDashAPIError as exc:
        await callback.message.edit_text(f"Не удалось сменить тариф: {exc.message}", reply_markup=back_keyboard(f"server:show:{vps_id}"))
        await callback.answer()
        return
    await callback.message.edit_text(
        f"Запрос на смену тарифа для заказа <code>{order_id}</code> отправлен.",
        reply_markup=back_keyboard(f"server:show:{vps_id}"),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("server:clone:"))
async def start_clone(callback: CallbackQuery, state: FSMContext, app_context: AppContext) -> None:
    source_vps_id = int(callback.data.rsplit(":", 1)[-1])
    items = await get_vps_items(app_context, force=True)
    targets = [item for item in items if item.get("id") != source_vps_id]
    if not targets:
        await callback.message.edit_text("Нет доступных целевых VPS для клонирования.", reply_markup=back_keyboard(f"server:show:{source_vps_id}"))
        await callback.answer()
        return
    await state.set_state(CloneStates.choose_targets)
    await state.update_data(clone_source_vps_id=source_vps_id, clone_targets=[])
    await _render_clone_targets(callback, state, targets)
    await callback.answer()


async def _render_clone_targets(callback: CallbackQuery, state: FSMContext, targets: list[dict[str, Any]]) -> None:
    data = await state.get_data()
    selected = set(data.get("clone_targets", []))
    source_vps_id = data["clone_source_vps_id"]
    builder = InlineKeyboardBuilder()
    for item in targets:
        target_id = item["id"]
        host = item.get("connection", {}).get("host") or str(target_id)
        prefix = "✅" if target_id in selected else "☑️"
        builder.button(text=f"{prefix} {host} · {target_id}", callback_data=f"clone:toggle:{target_id}")
    if selected:
        builder.button(text="Продолжить", callback_data="clone:confirm")
    builder.button(text="⬅️ Отмена", callback_data=f"server:show:{source_vps_id}")
    builder.adjust(1)
    await callback.message.edit_text(
        "Выберите от 1 до 5 целевых VPS для клонирования:",
        reply_markup=builder.as_markup(),
    )


@router.callback_query(CloneStates.choose_targets, F.data.startswith("clone:toggle:"))
async def toggle_clone_target(callback: CallbackQuery, state: FSMContext, app_context: AppContext) -> None:
    target_id = int(callback.data.rsplit(":", 1)[-1])
    data = await state.get_data()
    selected = set(data.get("clone_targets", []))
    if target_id in selected:
        selected.remove(target_id)
    else:
        if len(selected) >= 5:
            await callback.answer("Можно выбрать не более 5 VPS.", show_alert=True)
            return
        selected.add(target_id)
    await state.update_data(clone_targets=sorted(selected))
    items = await get_vps_items(app_context, force=False)
    targets = [item for item in items if item.get("id") != data["clone_source_vps_id"]]
    await _render_clone_targets(callback, state, targets)
    await callback.answer()


@router.callback_query(CloneStates.choose_targets, F.data == "clone:confirm")
async def confirm_clone(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    source_vps_id = data["clone_source_vps_id"]
    selected = data.get("clone_targets", [])
    if not selected:
        await callback.answer("Сначала выберите хотя бы один VPS.", show_alert=True)
        return
    await state.set_state(CloneStates.confirm)
    await callback.message.edit_text(
        f"Подтвердить клонирование VPS <code>{source_vps_id}</code> в цели: <code>{', '.join(map(str, selected))}</code>?",
        reply_markup=confirmation_keyboard("clone:do", f"server:show:{source_vps_id}"),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(CloneStates.confirm, F.data == "clone:do")
async def do_clone(callback: CallbackQuery, state: FSMContext, app_context: AppContext) -> None:
    data = await state.get_data()
    source_vps_id = data["clone_source_vps_id"]
    targets = data.get("clone_targets", [])
    try:
        async with app_context.guard.lock(f"clone:{source_vps_id}:{','.join(map(str, targets))}"):
            await app_context.client.clone_vps(source_vps_id=source_vps_id, target_vpses=targets)
            await app_context.cache.invalidate("vps:")
    except BusyOperationError:
        await callback.answer("Запрос уже обрабатывается. Подождите пару секунд.", show_alert=True)
        return
    except OneDashAPIError as exc:
        await callback.message.edit_text(f"Не удалось запустить клонирование: {exc.message}", reply_markup=back_keyboard(f"server:show:{source_vps_id}"))
        await callback.answer()
        return
    await state.clear()
    await callback.message.edit_text(
        f"Клонирование VPS <code>{source_vps_id}</code> запущено.",
        reply_markup=back_keyboard(f"server:show:{source_vps_id}"),
        parse_mode="HTML",
    )
    await callback.answer()
