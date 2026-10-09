import html

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from sqlalchemy.dialects.postgresql import insert

from app.db import SessionLocal
from app.models import User

router = Router()

WELCOME_TEXT = (
    "Привет, {name}! 👋\n\n"
    "Я <b>Женя</b> — твой AI-оператор путешествий ✈️\n\n"
    "Расскажи, куда хочешь поехать, на сколько дней и что тебе важно, "
    "а я подберу лучший вариант отпуска именно под тебя.\n\n"
    "Например: <i>«Хочу в Италию на неделю в мае, бюджет до 2000 €, "
    "поеду с собакой»</i>"
)


async def save_user(message: Message) -> None:
    tg_user = message.from_user
    stmt = insert(User).values(
        telegram_id=tg_user.id,
        username=tg_user.username,
        first_name=tg_user.first_name,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=[User.telegram_id],
        set_={
            "username": stmt.excluded.username,
            "first_name": stmt.excluded.first_name,
        },
    )
    async with SessionLocal() as session:
        await session.execute(stmt)
        await session.commit()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await save_user(message)
    name = html.escape(message.from_user.first_name or "путешественник")
    await message.answer(WELCOME_TEXT.format(name=name))