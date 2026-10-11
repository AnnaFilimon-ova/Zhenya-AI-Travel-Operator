from aiogram import Router
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo

from app.config import settings

router = Router()


@router.message(Command("app"))
async def cmd_app(message: Message) -> None:
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Открыть Женю ✈️",
                    web_app=WebAppInfo(url=settings.webapp_url),
                )
            ]
        ]
    )
    await message.answer("Настройки и карта — в мини-приложении:", reply_markup=keyboard)