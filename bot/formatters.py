from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def format_money(value: int | float | None, currency: str | None) -> str:
    if value is None:
        return "—"
    suffix = currency or ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return f"{value} {suffix}".strip()


def extract_price_for_period(tariff: dict[str, Any], period: int) -> dict[str, Any] | None:
    for item in tariff.get("prices", []):
        if item.get("period") == period:
            return item
    return None


def humanize_os_name(system_code: str, systems: list[dict[str, Any]]) -> str:
    for item in systems:
        if item.get("code") == system_code:
            return item.get("name") or system_code
    return system_code


def days_until(expires_at: int | None) -> int | None:
    if not expires_at:
        return None
    now = datetime.now(tz=UTC)
    target = datetime.fromtimestamp(expires_at, tz=UTC)
    delta = target - now
    return max(0, delta.days + (1 if delta.seconds > 0 else 0))


def format_server_card(vps: dict[str, Any], systems: list[dict[str, Any]], power: dict[str, Any] | None = None) -> str:
    host = vps.get("connection", {}).get("host") or "—"
    power_state = power.get("power_state") if power else ("running" if vps.get("active") else "stopped")
    action_status = power.get("power_action_status") if power else None
    days_left = days_until(vps.get("expires_at"))
    options = vps.get("options", {})
    options_text = ", ".join(
        label
        for enabled, label in [
            (options.get("static_ip"), "static IP"),
            (options.get("nvme"), "NVMe"),
            (options.get("backup"), "backup"),
        ]
        if enabled
    ) or "нет"
    lines = [
        "🖥 <b>Карточка VPS</b>",
        f"ID: <code>{vps.get('id')}</code>",
        f"IP: <code>{host}</code>",
        f"ОС: {humanize_os_name(vps.get('os', '—'), systems)}",
        f"Статус: {power_state}",
        f"Тариф: {vps.get('tariff', {}).get('name', '—')}",
        f"Локация: {vps.get('location', '—')} / {vps.get('processor', '—')}",
        f"Опции: {options_text}",
        f"Осталось дней: {days_left if days_left is not None else '—'}",
    ]
    if action_status:
        lines.append(f"Последняя операция питания: {action_status}")
    return "\n".join(lines)


def format_tariff_text(tariff: dict[str, Any], currency: str) -> str:
    config = tariff.get("config", {})
    prices = tariff.get("prices", [])
    prices_text = ", ".join(
        f"{price.get('period')} дн. — {format_money(price.get('price'), currency)}"
        for price in prices
    ) or "цены не указаны"
    return (
        f"• <b>{tariff.get('name')}</b> (ID {tariff.get('id')})\n"
        f"CPU: {config.get('cpu', '—')} | RAM: {config.get('ram', '—')} GB | Disk: {config.get('hard', '—')} GB\n"
        f"Цены: {prices_text}"
    )
