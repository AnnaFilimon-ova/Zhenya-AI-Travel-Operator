import asyncio

import pytest

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app import tickets

DDL = [
    "CREATE TABLE users (id INTEGER PRIMARY KEY, telegram_id INTEGER UNIQUE)",
    "CREATE TABLE cart_tickets (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, "
    "ticket_key TEXT NOT NULL, mode TEXT NOT NULL, origin TEXT NOT NULL, destination TEXT NOT NULL, "
    "depart_at TEXT, duration_min INTEGER, transfers INTEGER, car_key TEXT, url TEXT NOT NULL DEFAULT '', "
    "price_rub INTEGER NOT NULL, UNIQUE (user_id, ticket_key))",
]

PLANE = {
    "id": "MOW-AER-2026-12-15T09:15:00+03:00-4199", "mode": "plane", "origin": "MOW", "destination": "AER",
    "depart_at": "2026-12-15T09:15:00+03:00", "duration_min": 230, "price_rub": 4199, "transfers": 0,
    "url": "https://www.aviasales.ru/search/MOW1512AER1",
}
PLANE_2 = {
    "id": "MOW-TBS-2026-12-20-9000", "mode": "plane", "origin": "MOW", "destination": "TBS",
    "depart_at": None, "duration_min": 200, "price_rub": 9000, "transfers": 1, "url": "",
}


@pytest.fixture
def db(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite://")
    maker = async_sessionmaker(engine, expire_on_commit=False)

    async def setup():
        async with engine.begin() as conn:
            for stmt in DDL:
                await conn.execute(text(stmt))
            await conn.execute(text("INSERT INTO users (id, telegram_id) VALUES (1, 100), (2, 200)"))

    asyncio.run(setup())
    monkeypatch.setattr(tickets, "SessionLocal", maker)
    yield maker
    asyncio.run(engine.dispose())


def run(coro):
    return asyncio.run(coro)


def test_add_list_and_no_duplicates(db):
    first = run(tickets.add_ticket(100, PLANE))
    again = run(tickets.add_ticket(100, PLANE))
    assert first["already"] is False and again["already"] is True
    assert first["name"] == "Москва → Сочи" and first["subtotal"] == 4199 and first["type"] == "ticket"
    assert first["id"] == f"t{first['ticket_id']}"
    run(tickets.add_ticket(100, PLANE_2))
    items = run(tickets.list_tickets(100))
    assert [i["mode"] for i in items] == ["plane", "plane"]
    assert items[1]["depart_at"] is None and items[1]["transfers"] == 1


def test_tickets_belong_to_their_owner(db):
    item = run(tickets.add_ticket(100, PLANE))
    assert run(tickets.list_tickets(200)) == []
    assert run(tickets.remove_ticket(200, item["ticket_id"])) is False
    assert run(tickets.remove_ticket(100, item["ticket_id"])) is True
    assert run(tickets.list_tickets(100)) == []


def test_unknown_user_and_bad_options_are_rejected(db):
    assert run(tickets.add_ticket(999, PLANE)) is None
    for bad in ({**PLANE, "price_rub": -1}, {**PLANE, "mode": "bus"}, {**PLANE, "mode": "train"}, {**PLANE, "id": ""}, {**PLANE, "price_rub": True}):
        assert run(tickets.add_ticket(100, bad)) is None


def test_only_https_links_are_kept(db):
    item = run(tickets.add_ticket(100, {**PLANE, "url": "javascript:alert(1)"}))
    assert item["url"] == ""
    other = run(tickets.add_ticket(100, {**PLANE, "id": "x", "url": "https://example.com"}))
    assert other["url"] == "https://example.com"


def test_clear_tickets(db):
    run(tickets.add_ticket(100, PLANE))
    run(tickets.add_ticket(200, PLANE_2))

    async def clear():
        async with tickets.SessionLocal() as session:
            await tickets.clear_tickets(session, 1)
            await session.commit()

    run(clear())
    assert run(tickets.list_tickets(100)) == []
    assert len(run(tickets.list_tickets(200))) == 1
