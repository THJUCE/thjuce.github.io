from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from keyboards.common import main_menu_keyboard

router = Router()


async def send_main_menu(target: Message | CallbackQuery, *, reset_state: FSMContext | None = None) -> None:
    if reset_state:
        await reset_state.clear()
    text = "Добро пожаловать в OneDash Bot. Выберите действие:"
    markup = main_menu_keyboard()
    if isinstance(target, Message):
        await target.answer(text, reply_markup=markup)
    else:
        await target.message.edit_text(text, reply_markup=markup)
        await target.answer()


@router.message(CommandStart())
async def start_command(message: Message, state: FSMContext) -> None:
    await send_main_menu(message, reset_state=state)


@router.callback_query(F.data == "menu:root")
async def back_to_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await send_main_menu(callback, reset_state=state)
