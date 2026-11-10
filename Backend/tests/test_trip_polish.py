import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app import memory
from app.models import ChatMessage
from app.profile import profile_text


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def chat_db(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite://")
    maker = async_sessionmaker(engine, expire_on_commit=False)

    async def setup():
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    "CREATE TABLE chat_messages (id INTEGER PRIMARY KEY AUTOINCREMENT, telegram_id INTEGER NOT NULL, "
                    "role TEXT NOT NULL, text TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
                )
            )

    run(setup())
    monkeypatch.setattr(memory, "SessionLocal", maker)
    yield maker
    run(engine.dispose())


async def count(maker, telegram_id=None):
    async with maker() as session:
        query = select(ChatMessage)
        if telegram_id is not None:
            query = query.where(ChatMessage.telegram_id == telegram_id)
        return len((await session.execute(query)).scalars().all())


def test_history_is_trimmed_per_user(chat_db, monkeypatch):
    monkeypatch.setattr(memory, "KEEP_PER_USER", 6)

    async def fill():
        for i in range(10):
            await memory.save_exchange(1, f"q{i}", f"a{i}")
        await memory.save_exchange(2, "other", "other")

    run(fill())
    assert run(count(chat_db, 1)) <= 6 + 2
    assert run(count(chat_db, 2)) == 2
    history = run(memory.load_history(1))
    assert history[-1]["text"] == "a9"


def test_purge_old_messages(chat_db):
    async def fill():
        async with chat_db() as session:
            old = datetime.now(timezone.utc) - timedelta(days=40)
            session.add(ChatMessage(telegram_id=1, role="user", text="old", created_at=old))
            session.add(ChatMessage(telegram_id=1, role="user", text="fresh", created_at=datetime.now(timezone.utc)))
            await session.commit()

    run(fill())
    assert run(memory.purge_old_messages(30)) == 1
    assert run(count(chat_db)) == 1


def test_home_city_in_profile_text():
    assert "Home city" in profile_text({"home_city": "Казань"})
    assert "Home city" not in profile_text({"home_city": ""})
    assert 'Каз"ань' not in profile_text({"home_city": 'Каз"ань'})


def test_stay_nights():
    pytest.importorskip("google.genai")
    from app.agent.service import stay_nights

    assert stay_nights("2030-05-01", "2030-05-04") == 3
    assert stay_nights("2030-05-04", "2030-05-01") == 0
    assert stay_nights("2030-05-01", "2030-07-01") == 0
    assert stay_nights("", "") == 0
    assert stay_nights("bad", "2030-05-01") == 0


def test_hotel_button_shows_nights():
    pytest.importorskip("aiogram")
    from app.bot.handlers.cart import offered_keyboard

    keyboard = offered_keyboard([{"id": 7, "name": "Hotel A", "price": 3000, "nights": 3}])
    button = keyboard.inline_keyboard[0][0]
    assert "3 н." in button.text and "9000" in button.text and button.callback_data == "add:7:3"
    plain = offered_keyboard([{"id": 8, "name": "Hotel B", "price": 3000}]).inline_keyboard[0][0]
    assert plain.callback_data == "add:8" and "3000" in plain.text
