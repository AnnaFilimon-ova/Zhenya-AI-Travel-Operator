import asyncio
from datetime import date, timedelta
from statistics import median

from app.geo import CITY_CENTERS
from app.geocode import GeocodeError, resolve_center
from app.providers.base import ProviderUnavailable
from app.providers.registry import get_hotels, get_weather

MAX_CITIES = 4


def parse_dates(start_date: str, end_date: str) -> tuple[date, date]:
    try:
        start = date.fromisoformat(start_date) if start_date else date.today() + timedelta(days=7)
        end = date.fromisoformat(end_date) if end_date else start + timedelta(days=3)
    except ValueError:
        raise ValueError("dates must be YYYY-MM-DD") from None
    if end < start:
        start, end = end, start
    return start, end


async def _one(city: str, start: date, end: date) -> dict:
    result: dict = {"city": city}
    in_catalog = city in CITY_CENTERS
    center = CITY_CENTERS.get(city)
    if center is None:
        try:
            resolved = await resolve_center(city)
        except GeocodeError:
            return {**result, "error": "поиск города сейчас недоступен"}
        if resolved is None:
            return {**result, "error": "такой город не найден"}
        center = (resolved[0], resolved[1])
        result = {"city": resolved[2]}

    async def weather():
        try:
            return await get_weather().summary(center[0], center[1], start, end)
        except ProviderUnavailable:
            return {"error": "погода сейчас недоступна"}

    async def prices():
        found = await get_hotels().search(city, limit=30)
        values = [h["price_per_night_est"] for h in found["hotels"] if h.get("price_per_night_est")]
        return {
            "places_in_catalog": found["total_found"],
            "typical_price_per_night_est": round(median(values) / 100) * 100 if values else None,
        }

    if not in_catalog:
        return {**result, "weather": await weather(), "note": "каталога жилья по этому городу нет, цены не оцениваются"}
    weather_result, price_result = await asyncio.gather(weather(), prices())
    return {**result, "weather": weather_result, **price_result}


async def destination_overview(cities: list[str], start_date: str = "", end_date: str = "") -> dict:
    start, end = parse_dates(start_date, end_date)
    wanted = list(dict.fromkeys(cities))[:MAX_CITIES]
    return {
        "dates": [start.isoformat(), end.isoformat()],
        "cities": list(await asyncio.gather(*(_one(c, start, end) for c in wanted))),
        "note": (
            "Цены оценочные (по типу жилья, звёздам и городу), реальных цен и наличия нет. "
            "Время в пути до города здесь не считается: данные о транспорте не подключены."
        ),
    }
