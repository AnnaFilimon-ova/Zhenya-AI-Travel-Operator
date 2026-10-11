import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import MenuButtonWebApp, WebAppInfo

from app.bot.handlers import menu, start
from app.bot.middlewares import ThrottlingMiddleware
from app.config import settings


async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.message.middleware(ThrottlingMiddleware(delay=5))
    dp.include_router(start.router)
    dp.include_router(menu.router)

    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_chat_menu_button(
        menu_button=MenuButtonWebApp(
            text="Открыть Женю",
            web_app=WebAppInfo(url=settings.webapp_url),
        )
    )
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())