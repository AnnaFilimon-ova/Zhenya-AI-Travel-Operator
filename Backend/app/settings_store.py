import logging

from sqlalchemy import BigInteger, Column, DateTime, MetaData, String, Table, func, select
from sqlalchemy.dialects.postgresql import insert

from app.db import SessionLocal
from app.models import User

log = logging.getLogger(__name__)

PERSONAS = ("female", "male", "any")
DEFAULT_PERSONA = "any"

_metadata = MetaData()
user_settings = Table(
    "user_settings",
    _metadata,
    Column("user_id", BigInteger, primary_key=True),
    Column("persona", String, nullable=False, server_default=DEFAULT_PERSONA),
    Column("updated_at", DateTime(timezone=True), server_default=func.now()),
)


async def get_persona(telegram_id: int) -> str:
    try:
        async with SessionLocal() as session:
            user_id = (
                await session.execute(select(User.id).where(User.telegram_id == telegram_id))
            ).scalar_one_or_none()
            if user_id is None:
                return DEFAULT_PERSONA
            value = (
                await session.execute(
                    select(user_settings.c.persona).where(user_settings.c.user_id == user_id)
                )
            ).scalar_one_or_none()
    except Exception:
        log.exception("Не удалось прочитать настройки пользователя")
        return DEFAULT_PERSONA
    return value if value in PERSONAS else DEFAULT_PERSONA


async def set_persona(tg_user: dict, persona: str) -> str:
    if persona not in PERSONAS:
        raise ValueError("unknown persona")
    async with SessionLocal() as session:
        await session.execute(
            insert(User)
            .values(
                telegram_id=tg_user["id"],
                username=tg_user.get("username"),
                first_name=tg_user.get("first_name"),
            )
            .on_conflict_do_nothing(index_elements=[User.telegram_id])
        )
        user_id = (
            await session.execute(select(User.id).where(User.telegram_id == tg_user["id"]))
        ).scalar_one()
        stmt = insert(user_settings).values(user_id=user_id, persona=persona)
        await session.execute(
            stmt.on_conflict_do_update(
                index_elements=[user_settings.c.user_id],
                set_={"persona": stmt.excluded.persona, "updated_at": func.now()},
            )
        )
        await session.commit()
    return persona
