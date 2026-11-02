from sqlalchemy import text

from app.db import SessionLocal
from app.geo import resolve_city

MODES = ("plane", "train")

COLUMNS = "id, ticket_key, mode, origin, destination, depart_at, duration_min, transfers, car_key, url, price_rub"


def _city(value: str) -> str:
    return resolve_city(value) or value


def _item(row) -> dict:
    return {
        "type": "ticket",
        "id": f"t{row['id']}",
        "ticket_id": row["id"],
        "name": f"{row['origin']} → {row['destination']}",
        "mode": row["mode"],
        "origin": row["origin"],
        "destination": row["destination"],
        "depart_at": row["depart_at"],
        "duration_min": row["duration_min"],
        "transfers": row["transfers"],
        "car_key": row["car_key"],
        "url": row["url"],
        "price_rub": row["price_rub"],
        "subtotal": row["price_rub"],
    }


async def _user_id(session, telegram_id: int) -> int | None:
    row = (
        await session.execute(text("SELECT id FROM users WHERE telegram_id = :t"), {"t": telegram_id})
    ).first()
    return row[0] if row else None


def _clean(option: dict) -> dict | None:
    price = option.get("price_rub")
    key = option.get("id")
    if option.get("mode") not in MODES or not isinstance(key, str) or not key:
        return None
    if isinstance(price, bool) or not isinstance(price, (int, float)) or price < 0:
        return None
    url = option.get("url") or ""
    duration = option.get("duration_min")
    transfers = option.get("transfers")
    return {
        "key": key[:200],
        "mode": option["mode"],
        "origin": _city(str(option.get("origin") or ""))[:100],
        "destination": _city(str(option.get("destination") or ""))[:100],
        "depart_at": str(option["depart_at"])[:40] if option.get("depart_at") else None,
        "duration_min": int(duration) if isinstance(duration, (int, float)) and not isinstance(duration, bool) else None,
        "transfers": int(transfers) if isinstance(transfers, (int, float)) and not isinstance(transfers, bool) else None,
        "car_key": str(option["car_key"])[:30] if option.get("car_key") else None,
        "url": url[:500] if isinstance(url, str) and url.startswith("https://") else "",
        "price": int(round(price)),
    }


async def add_ticket(telegram_id: int, option: dict) -> dict | None:
    data = _clean(option)
    if data is None:
        return None
    async with SessionLocal() as session:
        user_id = await _user_id(session, telegram_id)
        if user_id is None:
            return None
        inserted = await session.execute(
            text(
                "INSERT INTO cart_tickets (user_id, ticket_key, mode, origin, destination, depart_at, "
                "duration_min, transfers, car_key, url, price_rub) "
                "VALUES (:u, :key, :mode, :origin, :destination, :depart_at, :duration_min, :transfers, "
                ":car_key, :url, :price) ON CONFLICT (user_id, ticket_key) DO NOTHING"
            ),
            {"u": user_id, **data},
        )
        await session.commit()
        row = (
            await session.execute(
                text(f"SELECT {COLUMNS} FROM cart_tickets WHERE user_id = :u AND ticket_key = :key"),
                {"u": user_id, "key": data["key"]},
            )
        ).mappings().first()
    result = _item(row)
    result["already"] = inserted.rowcount == 0
    return result


async def list_tickets(telegram_id: int) -> list[dict]:
    async with SessionLocal() as session:
        user_id = await _user_id(session, telegram_id)
        if user_id is None:
            return []
        rows = (
            await session.execute(
                text(f"SELECT {COLUMNS} FROM cart_tickets WHERE user_id = :u ORDER BY id"), {"u": user_id}
            )
        ).mappings().all()
    return [_item(r) for r in rows]


async def remove_ticket(telegram_id: int, ticket_id: int) -> bool:
    async with SessionLocal() as session:
        user_id = await _user_id(session, telegram_id)
        if user_id is None:
            return False
        result = await session.execute(
            text("DELETE FROM cart_tickets WHERE id = :i AND user_id = :u"), {"i": ticket_id, "u": user_id}
        )
        await session.commit()
        return result.rowcount > 0


async def clear_tickets(session, user_id: int) -> None:
    await session.execute(text("DELETE FROM cart_tickets WHERE user_id = :u"), {"u": user_id})
