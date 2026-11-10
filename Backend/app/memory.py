from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select

from app.db import SessionLocal
from app.models import ChatMessage

HISTORY_LIMIT = 30
KEEP_PER_USER = 200
KEEP_DAYS = 30


async def save_exchange(
    telegram_id: int,
    user_text: str,
    answer: str,
) -> None:
    if not isinstance(user_text, str):
        user_text = " ".join(map(str, user_text))

    if not isinstance(answer, str):
        answer = str(answer)

    async with SessionLocal() as session:
        session.add(
            ChatMessage(
                telegram_id=telegram_id,
                role="user",
                text=user_text,
            )
        )
        session.add(
            ChatMessage(
                telegram_id=telegram_id,
                role="model",
                text=answer,
            )
        )
        await session.commit()
        await _trim(session, telegram_id)


async def _trim(session, telegram_id: int, keep: int | None = None) -> None:
    keep = KEEP_PER_USER if keep is None else keep
    boundary = (
        await session.execute(
            select(ChatMessage.id)
            .where(ChatMessage.telegram_id == telegram_id)
            .order_by(ChatMessage.id.desc())
            .offset(keep)
            .limit(1)
        )
    ).scalar_one_or_none()
    if boundary is not None:
        await session.execute(
            delete(ChatMessage).where(
                ChatMessage.telegram_id == telegram_id, ChatMessage.id <= boundary
            )
        )
        await session.commit()


async def purge_old_messages(days: int = KEEP_DAYS) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    async with SessionLocal() as session:
        result = await session.execute(delete(ChatMessage).where(ChatMessage.created_at < cutoff))
        await session.commit()
        return result.rowcount or 0


async def load_history(telegram_id: int, limit: int = HISTORY_LIMIT) -> list[dict]:
    async with SessionLocal() as session:
        result = await session.execute(
            select(ChatMessage)
            .where(ChatMessage.telegram_id == telegram_id)
            .order_by(ChatMessage.id.desc())
            .limit(limit)
        )
        rows = list(reversed(result.scalars().all()))

    while rows and rows[0].role != "user":
        rows.pop(0)
    return [{"role": row.role, "text": row.text} for row in rows]


async def clear_history(telegram_id: int) -> None:
    async with SessionLocal() as session:
        await session.execute(
            delete(ChatMessage).where(ChatMessage.telegram_id == telegram_id)
        )
        await session.commit()