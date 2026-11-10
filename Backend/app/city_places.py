from app.geo import CITY_CENTERS
from app.geocode import GeocodeError, resolve_center
from app.nearby import CATEGORIES
from app.providers.base import ProviderUnavailable
from app.providers.registry import get_places

RADIUS = 2000
MAX_PLACES = 10


async def places_in_city(city: str, category: str, limit: int = 8) -> dict:
    if category not in CATEGORIES:
        return {"error": "неизвестная категория", "categories": list(CATEGORIES), "places": []}
    label = city
    center = CITY_CENTERS.get(city)
    if center is None:
        try:
            resolved = await resolve_center(city)
        except GeocodeError:
            return {"error": "поиск города сейчас недоступен, попробуй позже", "places": []}
        if resolved is None:
            return {"error": "такой город не найден: уточни название или добавь страну", "places": []}
        center, label = (resolved[0], resolved[1]), resolved[2]
    try:
        found = await get_places().search(category, center[0], center[1], RADIUS, limit=max(1, min(limit, MAX_PLACES)))
    except ProviderUnavailable:
        return {"error": "источник мест сейчас недоступен", "places": []}
    return {
        "city": label,
        "category": category,
        "area": f"центр города, радиус {RADIUS} м",
        "total_found": found["total"],
        "places": [
            {
                "name": p["name"],
                "kind": p["kind"],
                "address": p["address"],
                "distance_from_center_m": p["distance_m"],
                "cuisine": p["cuisine"],
                "notes": [b["text"] for b in p["badges"]],
                "website": p["website"],
            }
            for p in found["items"]
        ],
        "note": (
            "Данные OpenStreetMap: рейтингов и отзывов нет, часы работы и цены нужно проверять. "
            + ("Сейчас показана сохранённая копия данных, она может быть неполной." if found.get("offline") else "")
        ).strip(),
    }
