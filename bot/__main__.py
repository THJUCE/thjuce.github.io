from __future__ import annotations

import asyncio
import logging

from bot.app import create_dispatcher
from bot.logging_setup import configure_logging
from config import load_settings


async def main() -> None:
    settings = load_settings()
    configure_logging(settings)
    bot, dispatcher, context = create_dispatcher(settings)
    logging.getLogger(__name__).info("Starting OneDash bot")
    try:
        await dispatcher.start_polling(bot, app_context=context)
    finally:
        await context.client.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
