import html

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

router = Router()

WELCOME_TEXT = (
    "Привет, {name}! 👋\n\n"
    "Я <b>Женя</b> — твой AI-оператор путешествий ✈️\n\n"
    "Расскажи, куда хочешь поехать, на сколько дней и что тебе важно, "
    "а я подберу лучший вариант отпуска именно под тебя.\n\n"
    "Например: <i>«Хочу в Италию на неделю в мае, бюджет до 2000 €, "
    "поеду с собакой»</i>"
)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    name = html.escape(message.from_user.first_name or "путешественник")
    await message.answer(WELCOME_TEXT.format(name=name))