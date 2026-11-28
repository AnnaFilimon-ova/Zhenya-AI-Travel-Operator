
import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message
from google.genai import errors as genai_errors

from app.agent.service import ask, forget_chat, pop_offered, pop_offered_tickets
from app.bot.handlers.cart import offered_keyboard
from app.memory import clear_history, save_exchange

import tempfile
from pathlib import Path

from aiogram.types import FSInputFile
from app.agent.voice import transcribe_audio, synthesize_speech

MAX_USER_TEXT = 2000
router = Router()
log = logging.getLogger(__name__)


def split_text(text: str, limit: int = 4000) -> list[str]:
    return [text[i:i + limit] for i in range(0, len(text), limit)]


@router.message(Command("reset"))
async def cmd_reset(message: Message) -> None:
    await clear_history(message.from_user.id)
    forget_chat(message.from_user.id)
    await message.answer(
        "Начнём с чистого листа ✨ Нашу переписку я забыла, "
        "а профиль и настройки остались."
    )


@router.message(F.text, ~F.text.startswith("/"))
async def handle_text(message: Message) -> None:
    if len(message.text) > MAX_USER_TEXT:
        await message.answer("Сообщение слишком длинное, напиши покороче.")
        return

    await message.bot.send_chat_action(message.chat.id, "typing")

    try:
        answer = await ask(message.from_user.id, message.text)
    except genai_errors.ClientError as error:
        log.exception("Agent error")
        if getattr(error, "code", None) == 429:
            await message.answer(
                "Сейчас у меня закончился лимит запросов к ИИ, попробуй чуть позже 🙏"
            )
        else:
            await message.answer(
                "Что-то пошло не так, попробуй ещё раз чуть позже 🙏"
            )
        return
    except Exception:
        log.exception("Agent error")
        await message.answer(
            "Что-то пошло не так, попробуй ещё раз чуть позже 🙏"
        )
        return

    await save_exchange(message.from_user.id, message.text, answer)

    # Кнопки «добавить в корзину» для мест, которые агент показал в этом ответе.
    keyboard = offered_keyboard(
        pop_offered(message.from_user.id)
        + pop_offered_tickets(message.from_user.id)
    )

    parts = split_text(answer)
    for index, part in enumerate(parts):
        is_last = index == len(parts) - 1
        await message.answer(
            part,
            parse_mode=None,
            reply_markup=keyboard if is_last else None,
        )


@router.message(F.voice)

async def handle_voice(message: Message) -> None:
    await message.bot.send_chat_action(message.chat.id, "typing")

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "input.ogg"

            await message.bot.download(
                message.voice.file_id,
                destination=input_path,
            )

            # Незаметно распознаём голосовое сообщение.
            transcript = await transcribe_audio(str(input_path))

            if not transcript:
                await message.answer(
                    "Не получилось разобрать речь. Попробуй записать ещё раз."
                )
                return

            # Передаём распознанный текст Жене.
            await message.bot.send_chat_action(message.chat.id, "typing")
            answer = await ask(message.from_user.id, transcript)

            await save_exchange(
                message.from_user.id,
                transcript,
                answer,
            )

            keyboard = offered_keyboard(
                pop_offered(message.from_user.id)
                + pop_offered_tickets(message.from_user.id)
            )

            # Отправляем только ответ Жени обычным текстом.
            parts = split_text(answer)
            for index, part in enumerate(parts):
                await message.answer(
                    part,
                    parse_mode=None,
                    reply_markup=(
                        keyboard if index == len(parts) - 1 else None
                    ),
                )

    except Exception:
        log.exception("Voice processing error")
        await message.answer(
            "Не получилось обработать голосовое сообщение. "
            "Попробуй ещё раз чуть позже 🙏"
        )
