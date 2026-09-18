from __future__ import annotations

from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Баланс", callback_data="menu:balance")
    builder.button(text="🖥 Мои серверы", callback_data="menu:servers")
    builder.button(text="➕ Создать VPS", callback_data="menu:create")
    builder.button(text="💳 Пополнить баланс", callback_data="menu:topup")
    builder.button(text="📋 Тарифы", callback_data="menu:tariffs")
    builder.adjust(1)
    return builder.as_markup()


def back_keyboard(callback_data: str = "menu:root"):
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад", callback_data=callback_data)
    return builder.as_markup()


def confirmation_keyboard(confirm_data: str, cancel_data: str):
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить", callback_data=confirm_data)
    builder.button(text="❌ Отмена", callback_data=cancel_data)
    builder.adjust(2)
    return builder.as_markup()


def url_keyboard(text: str, url: str, back_callback: str = "menu:root"):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=text, url=url))
    builder.button(text="⬅️ В меню", callback_data=back_callback)
    return builder.as_markup()
