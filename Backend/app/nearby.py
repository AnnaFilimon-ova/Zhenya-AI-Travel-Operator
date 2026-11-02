"""Места рядом: рестораны, достопримечательности, культура, парки, вечер.

Источник: OpenStreetMap через Overpass API (лицензия ODbL, указываем авторство).
Рейтингов и отзывов в OSM нет, поэтому мы их не показываем и не придумываем.
Результаты кэшируются в памяти, чтобы не нагружать Overpass одинаковыми запросами.
"""
import asyncio
import json
import logging
import math
import time
from pathlib import Path

import httpx

from app.geo import CITY_CENTERS
from app.providers.base import ProviderUnavailable

OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]
log = logging.getLogger(__name__)
HEADERS = {"User-Agent": "ZhenyaTravelBot/0.1 (hackathon project)"}
CATEGORIES = {
    "food": {
        "label": "Поесть",
        "tags": [("amenity", ["restaurant", "cafe", "fast_food", "food_court"])],
    },
    "sights": {
        "label": "Достопримечательности",
        "tags": [
            ("tourism", ["attraction", "viewpoint"]),
            ("historic", ["monument", "memorial", "castle", "fort", "manor"]),
        ],
    },
    "culture": {
        "label": "Культура",
        "tags": [
            ("tourism", ["museum", "gallery"]),
            ("amenity", ["theatre", "cinema", "arts_centre"]),
        ],
    },
    "nature": {
        "label": "Парки и природа",
        "tags": [
            ("leisure", ["park", "garden", "nature_reserve"]),
            ("natural", ["beach"]),
        ],
    },
    "evening": {
        "label": "Вечер",
        "tags": [("amenity", ["bar", "pub", "nightclub"])],
    },
    "gothic": {
        "label": "Готика",
        "tags": [
            ("building", ["cathedral"]),
            ("building:architecture", ["gothic", "gothic_revival", "neo_gothic"]),
            ("architecture", ["gothic", "gothic_revival", "neo_gothic"]),
            ("historic", ["castle", "fort", "tomb", "monastery", "cemetery"]),
            ("amenity", ["monastery"]),
        ],
    },
    "beach": {
        "label": "Пляжи",
        "tags": [("natural", ["beach"]), ("leisure", ["beach_resort"])],
    },
    "active": {
        "label": "Активный отдых",
        "tags": [
            ("leisure", ["sports_centre", "water_park", "ice_rink"]),
            ("sport", ["climbing", "skiing"]),
        ],
    },
    "relax": {
        "label": "Спа и отдых",
        "tags": [("leisure", ["spa", "sauna", "resort"]), ("amenity", ["spa", "public_bath"])],
    },
    "music": {
        "label": "Музыка",
        "tags": [("amenity", ["music_venue", "arts_centre"])],
    },
    "shopping": {
        "label": "Шопинг",
        "tags": [("shop", ["mall", "department_store"]), ("amenity", ["marketplace"])],
    },
}

KIND_LABELS = {
    "restaurant": "ресторан", "cafe": "кафе", "fast_food": "фастфуд", "food_court": "фудкорт",
    "bar": "бар", "pub": "паб", "nightclub": "клуб",
    "museum": "музей", "gallery": "галерея", "theatre": "театр", "cinema": "кинотеатр",
    "arts_centre": "арт-центр", "music_venue": "музыкальная площадка",
    "attraction": "достопримечательность", "viewpoint": "смотровая площадка",
    "monument": "памятник", "memorial": "мемориал", "castle": "замок", "fort": "крепость",
    "manor": "усадьба", "tomb": "усыпальница", "monastery": "монастырь",
    "cemetery": "историческое кладбище", "cathedral": "собор",
    "park": "парк", "garden": "сад", "nature_reserve": "заповедник", "beach": "пляж",
    "beach_resort": "пляжный курорт",
    "sports_centre": "спортивный центр", "water_park": "аквапарк", "ice_rink": "каток",
    "spa": "спа", "sauna": "сауна", "public_bath": "баня", "resort": "курорт",
    "mall": "торговый центр", "department_store": "универмаг", "marketplace": "рынок",
}
GOTHIC_STYLES = {"gothic", "gothic_revival", "neo_gothic"}
CUISINES = {
    "italian": "итальянская", "japanese": "японская", "georgian": "грузинская",
    "russian": "русская", "chinese": "китайская", "uzbek": "узбекская", "pizza": "пицца",
    "sushi": "суши", "burger": "бургеры", "coffee_shop": "кофе", "steak_house": "стейки",
    "seafood": "морепродукты", "french": "французская", "armenian": "армянская",
    "turkish": "турецкая", "thai": "тайская", "vegetarian": "вегетарианская",
    "vegan": "веганская", "kebab": "кебаб", "regional": "региональная",
}
ALLOWED_RADIUS = (500, 1000, 2000)

_cache: dict[tuple, tuple[float, list]] = {}
CACHE_TTL = 30 * 60
CACHE_MAX = 200


class NearbyError(ProviderUnavailable):
    pass

def distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> int:
    r = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return round(2 * r * math.asin(math.sqrt(a)))


def build_query(category: str, lat: float, lon: float, radius: int, limit: int = 500) -> str:
    parts = "\n".join(
        f'  nwr["{key}"="{value}"]["name"](around:{radius},{lat:.5f},{lon:.5f});'
        for key, values in CATEGORIES[category]["tags"]
        for value in values
    )
    return f"[out:json][timeout:25];\n(\n{parts}\n);\nout center tags {limit};"


def _kind_key(tags: dict) -> str:
    if tags.get("building") == "cathedral":
        return "cathedral"
    for key in ("amenity", "tourism", "historic", "leisure", "natural", "shop"):
        value = tags.get(key)
        if value in KIND_LABELS:
            return value
    if (tags.get("building:architecture") or tags.get("architecture")) in GOTHIC_STYLES:
        return "gothic_building"
    return "place"


def _kind(tags: dict) -> str:
    key = _kind_key(tags)
    return KIND_LABELS.get(key) or {"gothic_building": "здание в готическом стиле"}.get(key, "место")


def _is_abandoned(tags: dict) -> bool:
    return any(
        k.startswith(("abandoned", "disused", "ruins")) or tags.get(k) in ("ruins",)
        for k in tags
    ) or tags.get("historic") == "ruins"


def _badges(tags: dict, food_prefs: list[str], accessible: bool, with_pets: bool) -> list[dict]:
    out = []
    vegan = tags.get("diet:vegan") in ("yes", "only")
    vegetarian = tags.get("diet:vegetarian") in ("yes", "only")
    halal = tags.get("diet:halal") in ("yes", "only")
    if vegan:
        out.append({"key": "vegan", "text": "есть веганское", "match": "vegan" in food_prefs})
    if vegetarian and not vegan:
        out.append({"key": "vegetarian", "text": "есть вегетарианское", "match": "vegetarian" in food_prefs})
    if halal:
        out.append({"key": "halal", "text": "халяль", "match": "halal" in food_prefs})
    if tags.get("wheelchair") == "yes":
        out.append({"key": "wheelchair", "text": "доступно на коляске", "match": accessible})
    if tags.get("dog") == "yes" or tags.get("pets") == "yes":
        out.append({"key": "dog", "text": "можно с собакой", "match": with_pets})
    return out


def _address(tags: dict) -> str:
    street, house = tags.get("addr:street"), tags.get("addr:housenumber")
    if street and house:
        return f"{street}, {house}"
    return street or ""


def parse_elements(
    elements: list[dict], lat: float, lon: float, food_prefs: list[str],
    accessible: bool, with_pets: bool,
) -> list[dict]:
    items, seen = [], set()
    for el in elements:
        tags = el.get("tags") or {}
        name = tags.get("name")
        if not name or _is_abandoned(tags):
            continue
        plat = el.get("lat") or (el.get("center") or {}).get("lat")
        plon = el.get("lon") or (el.get("center") or {}).get("lon")
        if plat is None or plon is None:
            continue
        key = (name.lower(), round(plat, 3), round(plon, 3))
        if key in seen:
            continue
        seen.add(key)
        cuisine_keys = [c for c in (tags.get("cuisine") or "").split(";") if c in CUISINES][:2]
        items.append(
            {
                "id": f'{el.get("type", "n")}{el.get("id")}',
                "name": name,
                "kind": _kind(tags),
                "kind_key": _kind_key(tags),
                "cuisine": ", ".join(CUISINES[c] for c in cuisine_keys),
                "cuisine_keys": cuisine_keys,
                "address": _address(tags),
                "distance_m": distance_m(lat, lon, plat, plon),
                "lat": plat,
                "lon": plon,
                "website": tags.get("website") or tags.get("contact:website") or "",
                "opening_hours": tags.get("opening_hours") or "",
                "badges": _badges(tags, food_prefs, accessible, with_pets),
            }
        )
    items.sort(key=lambda i: i["distance_m"])
    return items


async def _ask(client: httpx.AsyncClient, url: str, query: str) -> list[dict]:
    try:
        resp = await client.post(url, data={"data": query})
        resp.raise_for_status()
        data = resp.json()
        remark = str(data.get("remark") or "")
        if "error" in remark.lower() or "timed out" in remark.lower():
            raise ProviderUnavailable(f"Overpass: {remark[:80]}")
        return data.get("elements", [])
    except (httpx.HTTPError, ValueError, ProviderUnavailable) as exc:
        log.warning("Overpass %s: %s: %s", url, type(exc).__name__, exc)
        raise


async def fetch_overpass(query: str, timeout: float = 30) -> list[dict]:
    async with httpx.AsyncClient(timeout=timeout, headers=HEADERS) as client:
        tasks = [asyncio.create_task(_ask(client, url, query)) for url in OVERPASS_URLS]
        try:
            for finished in asyncio.as_completed(tasks):
                try:
                    return await finished
                except Exception:
                    continue
        finally:
            for task in tasks:
                task.cancel()
    raise NearbyError("все зеркала Overpass недоступны")

SEED_PATH = Path(__file__).resolve().parents[1] / "data" / "nearby_seed.json"
SEED_RADIUS_KM = 15
_seed: dict | None = None


def load_seed() -> dict:
    global _seed
    if _seed is None:
        try:
            _seed = json.loads(SEED_PATH.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            _seed = {}
    return _seed


def seed_elements(category: str, lat: float, lon: float) -> list[dict] | None:
    seed = load_seed()
    best, best_d = None, None
    for city, (clat, clon) in CITY_CENTERS.items():
        d = distance_m(lat, lon, clat, clon)
        if city in seed and category in seed[city] and (best_d is None or d < best_d):
            best, best_d = city, d
    if best is None or best_d > SEED_RADIUS_KM * 1000:
        return None
    return seed[best][category]


async def search_nearby(
    category: str, lat: float, lon: float, radius: int = 1000, limit: int = 40,
    food_prefs: list[str] | None = None, accessible: bool = False, with_pets: bool = False,
) -> dict:
    if category not in CATEGORIES:
        raise ValueError("unknown category")
    if radius not in ALLOWED_RADIUS:
        radius = 1000
    key = (category, round(lat, 3), round(lon, 3), radius)
    now = time.time()
    hit = _cache.get(key)
    offline = False
    if hit and now - hit[0] < CACHE_TTL:
        elements = hit[1]
    else:
        try:
            elements = await fetch_overpass(build_query(category, lat, lon, radius))
            if len(_cache) >= CACHE_MAX:
                _cache.clear()
            _cache[key] = (now, elements)
        except NearbyError:
            elements = seed_elements(category, lat, lon)
            if elements is None:
                raise
            offline = True
    items = parse_elements(elements, lat, lon, food_prefs or [], accessible, with_pets)
    items = [i for i in items if i["distance_m"] <= radius]
    return {
        "category": category, "radius": radius, "total": len(items),
        "items": items[:limit], "offline": offline,
    }
