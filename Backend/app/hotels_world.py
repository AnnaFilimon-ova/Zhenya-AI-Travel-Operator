import logging
import re

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from app.catalog import CURRENCY, PRICE_NOTE, _score, _to_dict, estimate_price, list_cities
from app.db import SessionLocal
from app.geo import CITY_CENTERS
from app.geocode import GeocodeError, resolve_center, search_lodging
from app.models import Hotel
from app.nearby import NearbyError, distance_m, fetch_overpass

log = logging.getLogger(__name__)

KINDS = ("hotel", "hostel", "guest_house", "apartment", "motel", "chalet")
RADII = (3000, 8000)
MIN_RESULTS = 3
MAX_ANCHOR_SHIFT_M = 30000
RANK_BUCKET_M = 400

_cache: dict[tuple, list[dict]] = {}


def build_query(lat: float, lon: float, radius: int) -> str:
    kinds = "|".join(KINDS)
    return (
        "[out:json][timeout:25];\n"
        f'nwr["tourism"~"^({kinds})$"]["name"](around:{radius},{lat:.5f},{lon:.5f});\n'
        "out center tags 120;"
    )


def _stars(value: str | None) -> int | None:
    first = (value or "").strip()[:1]
    return int(first) if first in ("1", "2", "3", "4", "5") else None


def _yes_no(tags: dict, *keys: str) -> bool | None:
    for key in keys:
        value = (tags.get(key) or "").lower()
        if value in ("yes", "true", "1"):
            return True
        if value in ("no", "false", "0"):
            return False
    return None


CONTROL = re.compile(r"[\x00-\x1f\x7f]")


def clean_text(value: str | None, limit: int = 160) -> str | None:
    if not value:
        return None
    text = CONTROL.sub(" ", str(value)).strip()
    return text[:limit] or None


def clean_url(value: str | None) -> str | None:
    text = clean_text(value, 200)
    return text if text and re.match(r"^https?://[^\s]+$", text) else None


def element_row(element: dict, city: str) -> dict | None:
    tags = element.get("tags") or {}
    name = (tags.get("name") or "").strip()
    kind = tags.get("tourism")
    if not name or kind not in KINDS:
        return None
    if element.get("type") == "node":
        lat, lon = element.get("lat"), element.get("lon")
    else:
        center = element.get("center") or {}
        lat, lon = center.get("lat"), center.get("lon")
    if lat is None or lon is None:
        return None
    address = clean_text(", ".join(p for p in (tags.get("addr:street"), tags.get("addr:housenumber")) if p))
    return {
        "osm_type": element["type"],
        "osm_id": element["id"],
        "name": clean_text(name, 120) or "",
        "kind": kind,
        "city": city,
        "address": address,
        "lat": lat,
        "lon": lon,
        "stars": _stars(tags.get("stars")),
        "website": clean_url(tags.get("website") or tags.get("contact:website")),
        "phone": clean_text(tags.get("phone") or tags.get("contact:phone"), 40),
        "wheelchair": tags.get("wheelchair"),
        "pets": _yes_no(tags, "pets", "dog", "pets_allowed", "pet"),
        "tags": tags,
    }


async def _save(rows: list[dict]) -> list[Hotel]:
    if not rows:
        return []
    async with SessionLocal() as session:
        stmt = insert(Hotel).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["osm_type", "osm_id"],
            set_={c: stmt.excluded[c] for c in ("name", "kind", "address", "lat", "lon", "stars", "website", "phone", "wheelchair", "pets", "tags")},
        )
        await session.execute(stmt)
        await session.commit()
        out = []
        for row in rows:
            hotel = (
                await session.execute(
                    select(Hotel).where(Hotel.osm_type == row["osm_type"], Hotel.osm_id == row["osm_id"])
                )
            ).scalar_one_or_none()
            if hotel:
                out.append(hotel)
        return out


async def _live(lat: float, lon: float, city: str) -> list[Hotel]:
    found: list[dict] = []
    for radius in RADII:
        key = (round(lat, 3), round(lon, 3), radius)
        cached = _cache.get(key)
        if cached is None:
            try:
                elements = await fetch_overpass(build_query(lat, lon, radius), timeout=25)
            except NearbyError:
                log.warning("Overpass is down, falling back to Nominatim for hotels")
                try:
                    elements = await search_lodging(lat, lon, radius)
                except GeocodeError:
                    raise NearbyError("hotel sources are unavailable") from None
            cached = [r for el in elements if (r := element_row(el, city))]
            if cached:
                if len(_cache) > 200:
                    _cache.clear()
                _cache[key] = cached
        found = cached
        if len(found) >= MIN_RESULTS:
            break
    return await _save(found)


async def _center(city: str, near_place: str) -> tuple[float, float, str, str | None]:
    if city in CITY_CENTERS:
        clat, clon = CITY_CENTERS[city]
        label = city
    else:
        hit = await resolve_center(city)
        if hit is None:
            raise LookupError("city not found")
        clat, clon, label = hit
    if near_place:
        try:
            anchor = await resolve_center(f"{near_place}, {city}")
        except GeocodeError:
            anchor = None
        if anchor and distance_m(clat, clon, anchor[0], anchor[1]) <= MAX_ANCHOR_SHIFT_M:
            return anchor[0], anchor[1], label, near_place
    return clat, clon, label, None


async def _catalog_hotels(city: str) -> list[Hotel]:
    async with SessionLocal() as session:
        return list(
            (await session.execute(select(Hotel).where(func.lower(Hotel.city) == city.strip().lower()))).scalars().all()
        )


async def search_near(
    city: str,
    near_place: str = "",
    kinds: list[str] | None = None,
    min_stars: int | None = None,
    want_pets: bool = False,
    want_accessible: bool = False,
    only_confirmed: bool = False,
    name_query: str | None = None,
    max_price: int | None = None,
    limit: int = 5,
) -> dict:
    try:
        lat, lon, label, anchor = await _center(city, near_place.strip())
    except LookupError:
        return {"city": city, "total_found": 0, "hotels": [], "error": "такой город не найден: уточни название или добавь страну"}
    except GeocodeError:
        return {"city": city, "total_found": 0, "hotels": [], "error": "поиск города сейчас недоступен, попробуй позже"}

    catalog = {c["city"].lower() for c in await list_cities()}
    if city.strip().lower() in catalog:
        hotels = await _catalog_hotels(city)
        source = "catalog"
    else:
        try:
            hotels = await _live(lat, lon, label)
        except NearbyError:
            return {"city": label, "total_found": 0, "hotels": [], "error": "источник отелей сейчас недоступен, попробуй позже"}
        source = "live"

    if kinds:
        hotels = [h for h in hotels if h.kind in kinds]
    if min_stars:
        hotels = [h for h in hotels if (h.stars or 0) >= min_stars]
    if name_query:
        hotels = [h for h in hotels if name_query.strip().lower() in h.name.lower()]
    if only_confirmed and want_pets:
        hotels = [h for h in hotels if h.pets is True]
    if only_confirmed and want_accessible:
        hotels = [h for h in hotels if h.wheelchair in ("yes", "limited")]
    if max_price:
        hotels = [h for h in hotels if estimate_price(h) <= max_price]

    dist = {h.id: distance_m(lat, lon, h.lat, h.lon) for h in hotels}
    hotels.sort(key=lambda h: (dist[h.id] // RANK_BUCKET_M, -_score(h, want_pets, want_accessible)))
    out = []
    for h in hotels[: max(1, min(limit, 10))]:
        item = _to_dict(h)
        item["distance_to_place_m"] = dist[h.id]
        out.append(item)
    log.info(
        "hotels search city=%r near=%r center=%.4f,%.4f source=%s found=%d",
        city, near_place, lat, lon, source, len(hotels),
    )
    return {
        "city": label,
        "near": anchor or "центр города",
        "near_found": bool(anchor) or not near_place,
        "searched_around": {"lat": round(lat, 4), "lon": round(lon, 4)},
        "total_found": len(hotels),
        "hotels": out,
        "currency": CURRENCY,
        "note": (
            "Источник: OpenStreetMap, отели отсортированы по расстоянию до выбранного места. "
            + ("Выбранное место не удалось найти на карте, поэтому расстояния считаются от центра города. " if near_place and not anchor else "")
            + ("В радиусе 8 км отелей не нашлось: скажи об этом и не ищи в другом городе. " if not hotels else "")
            + f"Рейтингов и реальных цен нет. {PRICE_NOTE} "
            + ("Цена для города вне каталога очень приблизительная. " if source == "live" else "")
            + "pets/wheelchair = unknown означает, что данных нет, а не что нельзя."
        ),
    }
