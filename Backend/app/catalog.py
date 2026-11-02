from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import Hotel

KIND_LABELS = {
    "hotel": "отель",
    "hostel": "хостел",
    "guest_house": "гостевой дом",
    "apartment": "апартаменты",
    "motel": "мотель",
    "chalet": "шале",
}

CURRENCY = "RUB"
PRICE_NOTE = "Оценочная цена за ночь, не реальная. Точную цену нужно смотреть на сайте или у отеля."
HOTEL_BASE_BY_STARS = {None: 4000, 1: 2500, 2: 3200, 3: 4500, 4: 7000, 5: 13000}
OTHER_BASE = {"guest_house": 3200, "apartment": 4200, "motel": 3000, "chalet": 5500}
CITY_FACTOR = {
    "москва": 1.6,
    "санкт-петербург": 1.45,
    "сочи": 1.35,
    "калининград": 1.1,
    "казань": 1.05,
    "екатеринбург": 1.0,
    "нижний новгород": 0.95,
    "иркутск": 0.95,
    "кисловодск": 0.9,
    "рязань": 0.75,
}
DEFAULT_CITY_FACTOR = 0.9


def estimate_price(hotel: Hotel) -> int:
    if hotel.kind == "hostel":
        base = 1100 + 250 * (hotel.stars or 0)
    elif hotel.kind == "hotel":
        base = HOTEL_BASE_BY_STARS.get(hotel.stars, HOTEL_BASE_BY_STARS[None])
    else:
        base = OTHER_BASE.get(hotel.kind, 3500)

    factor = CITY_FACTOR.get((hotel.city or "").strip().lower(), DEFAULT_CITY_FACTOR)
    jitter = ((hotel.osm_id * 2654435761) % 31 - 15) / 100
    price = base * factor * (1 + jitter)
    return int(round(price / 100.0) * 100)


def _status(value: bool | None) -> str:
    if value is True:
        return "yes"
    if value is False:
        return "no"
    return "unknown"


def _to_dict(hotel: Hotel) -> dict:
    return {
        "id": hotel.id,
        "name": hotel.name,
        "kind": hotel.kind,
        "kind_label": KIND_LABELS.get(hotel.kind, hotel.kind),
        "city": hotel.city,
        "address": hotel.address,
        "stars": hotel.stars,
        "website": hotel.website,
        "phone": hotel.phone,
        "lat": hotel.lat,
        "lon": hotel.lon,
        "pets": _status(hotel.pets),
        "wheelchair": hotel.wheelchair or "unknown",
        "price_per_night_est": estimate_price(hotel),
        "currency": CURRENCY,
    }


def _score(hotel: Hotel, want_pets: bool, want_accessible: bool) -> float:
    score = 0.0
    score += (hotel.stars or 0) * 2
    if hotel.website:
        score += 1.5
    if hotel.phone:
        score += 0.5
    if want_pets:
        score += 5 if hotel.pets is True else 0
    if want_accessible:
        score += 5 if hotel.wheelchair == "yes" else (2 if hotel.wheelchair == "limited" else 0)
    return score


async def list_cities() -> list[dict]:
    async with SessionLocal() as session:
        rows = await session.execute(
            select(Hotel.city, func.count()).group_by(Hotel.city).order_by(Hotel.city)
        )
        return [{"city": city, "count": count} for city, count in rows.all()]


async def get_hotel(hotel_id: int) -> Hotel | None:
    async with SessionLocal() as session:
        return await session.get(Hotel, hotel_id)


async def search_catalog(
    city: str,
    kinds: list[str] | None = None,
    min_stars: int | None = None,
    want_pets: bool = False,
    want_accessible: bool = False,
    only_confirmed: bool = False,
    name_query: str | None = None,
    max_price: int | None = None,
    limit: int = 10,
) -> dict:
    query = select(Hotel).where(func.lower(Hotel.city) == city.strip().lower())
    if kinds:
        query = query.where(Hotel.kind.in_(kinds))
    if min_stars:
        query = query.where(Hotel.stars >= min_stars)
    if name_query:
        query = query.where(Hotel.name.ilike(f"%{name_query.strip()}%"))
    if only_confirmed and want_pets:
        query = query.where(Hotel.pets.is_(True))
    if only_confirmed and want_accessible:
        query = query.where(Hotel.wheelchair.in_(["yes", "limited"]))

    async with SessionLocal() as session:
        hotels = (await session.execute(query)).scalars().all()

    if max_price:
        hotels = [h for h in hotels if estimate_price(h) <= max_price]

    hotels = sorted(
        hotels, key=lambda h: _score(h, want_pets, want_accessible), reverse=True
    )
    return {
        "city": city,
        "total_found": len(hotels),
        "hotels": [_to_dict(h) for h in hotels[: max(1, min(limit, 30))]],
        "note": (
            "Источник: OpenStreetMap. Рейтингов и реальных цен нет. "
            f"{PRICE_NOTE} "
            "pets/wheelchair = unknown означает, что данных нет, а не что нельзя."
        ),
    }
