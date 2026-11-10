import secrets
import string

from sqlalchemy import delete, select

from app.catalog import CURRENCY, KIND_LABELS, estimate_price
from app.db import SessionLocal
from app.models import CartItem, Hotel, Order, User
from app.tickets import clear_tickets, list_tickets

MAX_NIGHTS = 30


async def _user_id(session, telegram_id: int) -> int | None:
    return (
        await session.execute(select(User.id).where(User.telegram_id == telegram_id))
    ).scalar_one_or_none()


def _item_dict(item: CartItem, hotel: Hotel) -> dict:
    price = estimate_price(hotel)
    return {
        "type": "hotel",
        "id": item.id,
        "hotel_id": hotel.id,
        "kind": hotel.kind,
        "name": hotel.name,
        "kind_label": KIND_LABELS.get(hotel.kind, hotel.kind),
        "city": hotel.city,
        "address": hotel.address,
        "stars": hotel.stars,
        "website": hotel.website,
        "nights": item.nights,
        "price_per_night_est": price,
        "subtotal": price * item.nights,
    }


async def add_to_cart(telegram_id: int, hotel_id: int, nights: int = 1) -> dict | None:
    nights = max(1, min(int(nights), MAX_NIGHTS))
    async with SessionLocal() as session:
        user_id = await _user_id(session, telegram_id)
        hotel = await session.get(Hotel, hotel_id)
        if user_id is None or hotel is None:
            return None
        item = (
            await session.execute(
                select(CartItem).where(
                    CartItem.user_id == user_id, CartItem.hotel_id == hotel_id
                )
            )
        ).scalar_one_or_none()
        already = item is not None
        if item is not None and nights != 1 and item.nights != nights:
            item.nights = nights
            await session.commit()
        if item is None:
            item = CartItem(user_id=user_id, hotel_id=hotel_id, nights=nights)
            session.add(item)
            await session.commit()
            await session.refresh(item)
        result = _item_dict(item, hotel)
        result["already"] = already
        return result


async def get_cart(telegram_id: int) -> dict:
    async with SessionLocal() as session:
        user_id = await _user_id(session, telegram_id)
        items: list[dict] = []
        if user_id is not None:
            rows = (
                await session.execute(
                    select(CartItem, Hotel)
                    .join(Hotel, Hotel.id == CartItem.hotel_id)
                    .where(CartItem.user_id == user_id)
                    .order_by(CartItem.id)
                )
            ).all()
            items = [_item_dict(item, hotel) for item, hotel in rows]
    items += await list_tickets(telegram_id)
    return {
        "items": items,
        "total": sum(i["subtotal"] for i in items),
        "currency": CURRENCY,
        "estimate": True,
    }


async def set_nights(telegram_id: int, item_id: int, nights: int) -> bool:
    nights = max(1, min(int(nights), MAX_NIGHTS))
    async with SessionLocal() as session:
        user_id = await _user_id(session, telegram_id)
        item = await session.get(CartItem, item_id)
        if user_id is None or item is None or item.user_id != user_id:
            return False
        item.nights = nights
        await session.commit()
        return True


async def remove_item(telegram_id: int, item_id: int) -> bool:
    async with SessionLocal() as session:
        user_id = await _user_id(session, telegram_id)
        item = await session.get(CartItem, item_id)
        if user_id is None or item is None or item.user_id != user_id:
            return False
        await session.delete(item)
        await session.commit()
        return True


async def list_orders(telegram_id: int, limit: int = 5) -> list[dict]:
    async with SessionLocal() as session:
        user_id = await _user_id(session, telegram_id)
        if user_id is None:
            return []
        rows = (
            await session.execute(
                select(Order)
                .where(Order.user_id == user_id)
                .order_by(Order.id.desc())
                .limit(limit)
            )
        ).scalars().all()
        return [
            {
                "code": o.code,
                "total": o.total,
                "currency": CURRENCY,
                "created_at": o.created_at.isoformat(),
                "provider": o.provider,
                "items": o.items,
            }
            for o in rows
        ]


def _new_code() -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "ZH-" + "".join(secrets.choice(alphabet) for _ in range(6))


async def checkout(
    telegram_id: int, provider: str = "demo", payment_ref: str | None = None
) -> dict | None:
    cart = await get_cart(telegram_id)
    if not cart["items"]:
        return None
    async with SessionLocal() as session:
        user_id = await _user_id(session, telegram_id)
        if user_id is None:
            return None
        order = Order(
            user_id=user_id,
            code=_new_code(),
            total=cart["total"],
            status="paid",
            provider=provider,
            payment_ref=payment_ref,
            items=cart["items"],
        )
        session.add(order)
        await session.execute(delete(CartItem).where(CartItem.user_id == user_id))
        await clear_tickets(session, user_id)
        await session.commit()
        await session.refresh(order)
        return {
            "code": order.code,
            "total": order.total,
            "currency": CURRENCY,
            "items": order.items,
            "provider": provider,
            "demo": True,
        }
