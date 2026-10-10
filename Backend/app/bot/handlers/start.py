import html

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from sqlalchemy import update
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


class Registration(StatesGroup):
    waiting_name = State()


async def save_user(message: Message) -> str | None:
    """Создаёт или обновляет пользователя, возвращает его display_name."""
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
    ).returning(User.display_name)
    async with SessionLocal() as session:
        result = await session.execute(stmt)
        await session.commit()
        return result.scalar_one()


async def set_display_name(telegram_id: int, name: str) -> None:
    async with SessionLocal() as session:
        await session.execute(
            update(User)
            .where(User.telegram_id == telegram_id)
            .values(display_name=name)
        )
        await session.commit()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    display_name = await save_user(message)

    if display_name:
        await state.clear()
        await message.answer(WELCOME_TEXT.format(name=html.escape(display_name)))
        return

    first_name = message.from_user.first_name
    keyboard = None
    if first_name:
        keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=first_name)]],
            resize_keyboard=True,
            one_time_keyboard=True,
            input_field_placeholder="Или напиши своё имя",
        )

    await state.set_state(Registration.waiting_name)
    await message.answer(
        "Привет! Я <b>Женя</b> ✈️\nКак к тебе обращаться?\n\n"
        "Нажми кнопку с твоим именем из Telegram или напиши своё.",
        reply_markup=keyboard,
    )


@router.message(Registration.waiting_name, F.text)
async def process_name(message: Message, state: FSMContext) -> None:
    name = message.text.strip()

    if not name or name.startswith("/"):
        await message.answer("Напиши, пожалуйста, имя обычным текстом 🙂")
        return

    name = name[:50]
    await set_display_name(message.from_user.id, name)
    await state.clear()
    await message.answer(
        WELCOME_TEXT.format(name=html.escape(name)),
        reply_markup=ReplyKeyboardRemove(),
    )