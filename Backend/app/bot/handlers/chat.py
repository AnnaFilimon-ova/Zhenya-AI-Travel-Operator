import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from app.agent.service import ask, forget_chat
from app.memory import clear_history, save_exchange

router = Router()
log = logging.getLogger(__name__)


def split_text(text: str, limit: int = 4000) -> list[str]:
    return [text[i:i + limit] for i in range(0, len(text), limit)]


@router.message(Command("reset"))
async def cmd_reset(message: Message) -> None:
    await clear_history(message.from_user.id)
    await clear_history(message.from_user.id)
    forget_chat(message.from_user.id)
    await message.answer(
        "Начнём с чистого листа ✨ Нашу переписку я забыла, "
        "а профиль и настройки остались."
    )


@router.message(F.text, ~F.text.startswith("/"))
async def handle_text(message: Message) -> None:
    await message.bot.send_chat_action(message.chat.id, "typing")
    try:
        answer = await ask(message.from_user.id, message.text)
    except Exception:
        log.exception("Agent error")
        await message.answer("Что-то пошло не так, попробуй ещё раз чуть позже 🙏")
        return

    await save_exchange(message.from_user.id, message.text, answer)
    for part in split_text(answer):
        await message.answer(part, parse_mode=None)