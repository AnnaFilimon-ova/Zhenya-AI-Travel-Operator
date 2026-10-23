from sqlalchemy import delete, select

from app.db import SessionLocal
from app.models import ChatMessage

HISTORY_LIMIT = 30


async def save_exchange(telegram_id: int, user_text: str, answer: str) -> None:
    async with SessionLocal() as session:
        session.add(ChatMessage(telegram_id=telegram_id, role="user", text=user_text))
        session.add(ChatMessage(telegram_id=telegram_id, role="model", text=answer))
        await session.commit()


async def load_history(telegram_id: int, limit: int = HISTORY_LIMIT) -> list[dict]:
    """Последние сообщения, от старых к новым. Начинается с реплики пользователя."""
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