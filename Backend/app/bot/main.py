import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import MenuButtonWebApp, WebAppInfo

from app.bot.handlers import cart, chat, menu, start
from app.bot.middlewares import ThrottlingMiddleware
from app.config import settings
from app.memory import purge_old_messages

log = logging.getLogger(__name__)

PURGE_EVERY_SECONDS = 6 * 3600


async def purge_loop() -> None:
    while True:
        try:
            removed = await purge_old_messages()
            if removed:
                log.info("Удалено старых сообщений: %s", removed)
        except Exception:
            log.exception("Не удалось почистить старую переписку")
        await asyncio.sleep(PURGE_EVERY_SECONDS)


async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    if not settings.bot_token:
        log.warning("BOT_TOKEN не задан: Telegram-бот отключён. Веб-версия работает без него.")
        return

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.message.middleware(ThrottlingMiddleware(delay=5))
    dp.include_router(start.router)
    dp.include_router(menu.router)
    dp.include_router(cart.router)
    dp.include_router(chat.router)

    await bot.delete_webhook(drop_pending_updates=True)
    if settings.webapp_url.startswith("https://"):
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="Открыть Женю",
                web_app=WebAppInfo(url=settings.webapp_url),
            )
        )
    else:
        log.warning("WEBAPP_URL не https: кнопка мини-аппа в Telegram не создаётся.")
    purge_task = asyncio.create_task(purge_loop())
    try:
        await dp.start_polling(bot)
    finally:
        purge_task.cancel()


if __name__ == "__main__":
    asyncio.run(main())
