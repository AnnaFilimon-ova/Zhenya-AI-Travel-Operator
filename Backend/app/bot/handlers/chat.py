import logging

from aiogram import F, Router
from aiogram.types import Message

from app.agent.service import ask

router = Router()
log = logging.getLogger(__name__)


def split_text(text: str, limit: int = 4000) -> list[str]:
    return [text[i:i + limit] for i in range(0, len(text), limit)]


@router.message(F.text, ~F.text.startswith("/"))
async def handle_text(message: Message) -> None:
    await message.bot.send_chat_action(message.chat.id, "typing")
    try:
        answer = await ask(message.from_user.id, message.text)
    except Exception:
        log.exception("Agent error")
        await message.answer("Что-то пошло не так, попробуй ещё раз чуть позже 🙏")
        return
    for part in split_text(answer):
        await message.answer(part, parse_mode=None)