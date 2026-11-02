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
from app.config import settings

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
            await message.answer("Что-то пошло не так, попробуй ещё раз чуть позже 🙏")
        return
    except Exception:
        log.exception("Agent error")
        await message.answer("Что-то пошло не так, попробуй ещё раз чуть позже 🙏")
        return

    await save_exchange(message.from_user.id, message.text, answer)

    # Кнопки «добавить в корзину» для мест, которые агент показал в этом ответе.
    keyboard = offered_keyboard(
        pop_offered(message.from_user.id), pop_offered_tickets(message.from_user.id)
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
    if not settings.groq_api_key:
        await message.answer(
            "Голосовой режим пока не настроен: добавь GROQ_API_KEY в .env."
        )
        return

    await message.bot.send_chat_action(message.chat.id, "typing")
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "input.ogg"
            output_path = Path(temp_dir) / "zhenya.mp3"

            await message.bot.download(
                message.voice.file_id,
                destination=input_path,
            )

            transcript = await transcribe_audio(str(input_path))

            if not transcript:
                await message.answer(
                    "Я не смогла разобрать речь. Попробуй записать ещё раз."
                )
                return

            await message.bot.send_chat_action(message.chat.id, "typing")
            answer = await ask(message.from_user.id, transcript)

            await save_exchange(
                message.from_user.id,
                transcript,
                answer,
            )

            keyboard = offered_keyboard(
                pop_offered_tickets(message.from_user.id),
                pop_offered_tickets(message.from_user.id),
            )

            await message.answer(
                f"🎧 Я услышала: {transcript}",
                parse_mode=None,
            )

            parts = split_text(answer)
            for index, part in enumerate(parts):
                await message.answer(
                    part,
                    parse_mode=None,
                    reply_markup=(
                        keyboard if index == len(parts) - 1 else None
                    ),
                )

            # Озвучиваем ответ. Для первой версии ограничиваем
            # длину аудио, чтобы длинный ответ не создавал проблем.
            speech_text = answer[:2500]
            await synthesize_speech(
                speech_text,
                str(output_path),
            )

            await message.answer_audio(
                audio=FSInputFile(output_path),
                title="Ответ Жени",
            )

    except Exception:
        log.exception("Voice processing error")
        await message.answer(
            "Не получилось обработать голосовое сообщение. "
            "Попробуй ещё раз чуть позже 🙏"
        )
