import asyncio
import math
import re
import time

import httpx

from app.geo import CITY_CENTERS
from app.providers.base import ProviderUnavailable

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
HEADERS = {"User-Agent": "ZhenyaTravelBot/0.1 (hackathon project)"}
CACHE_TTL = 24 * 3600
CACHE_MAX = 500
MIN_GAP = 1.1
MAX_QUERY = 80

_cache: dict[tuple[str, str], tuple[float, list[dict]]] = {}
_lock = asyncio.Lock()
_last_call = 0.0


class GeocodeError(ProviderUnavailable):
    pass


def clean_query(query: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[\x00-\x1f]", " ", query or "")).strip()[:MAX_QUERY]


def local_matches(query: str) -> list[dict]:
    q = query.casefold()
    return [
        {"name": city, "label": f"{city}, Россия", "lat": lat, "lon": lon, "country": "Россия"}
        for city, (lat, lon) in CITY_CENTERS.items()
        if city.casefold().startswith(q)
    ]


def _label(item: dict, name: str) -> str:
    address = item.get("address") or {}
    parts = [name]
    region = address.get("state") or address.get("region") or address.get("county")
    if region and region != name:
        parts.append(region)
    country = address.get("country")
    if country:
        parts.append(country)
    return ", ".join(parts)


def parse_results(data: list[dict]) -> list[dict]:
    out, seen = [], set()
    for item in data:
        try:
            lat, lon = float(item["lat"]), float(item["lon"])
        except (KeyError, TypeError, ValueError):
            continue
        name = item.get("name") or (item.get("display_name") or "").split(",")[0].strip()
        if not name:
            continue
        address = item.get("address") or {}
        key = (name.casefold(), round(lat, 1), round(lon, 1))
        if key in seen:
            continue
        seen.add(key)
        out.append(
            {
                "name": name,
                "label": _label(item, name),
                "lat": lat,
                "lon": lon,
                "country": address.get("country", ""),
            }
        )
    return out


async def search_places(query: str, lang: str = "ru", limit: int = 6) -> list[dict]:
    query = clean_query(query)
    if len(query) < 2:
        return []
    lang = "en" if lang == "en" else "ru"
    local = local_matches(query) if lang == "ru" else []
    key = (query.casefold(), lang)
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < CACHE_TTL:
        remote = hit[1]
    else:
        remote = await _ask(query, lang)
        if len(_cache) >= CACHE_MAX:
            _cache.clear()
        _cache[key] = (time.time(), remote)
    names = {r["name"].casefold() for r in local}
    return (local + [r for r in remote if r["name"].casefold() not in names])[:limit]


async def _ask(query: str, lang: str) -> list[dict]:
    global _last_call
    params = {
        "q": query,
        "format": "jsonv2",
        "limit": 8,
        "addressdetails": 1,
        "featuretype": "settlement",
        "accept-language": lang,
    }
    async with _lock:
        wait = MIN_GAP - (time.monotonic() - _last_call)
        if wait > 0:
            await asyncio.sleep(wait)
        try:
            async with httpx.AsyncClient(timeout=10, headers=HEADERS) as client:
                resp = await client.get(NOMINATIM_URL, params=params)
                resp.raise_for_status()
                data = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise GeocodeError(f"Nominatim: {type(exc).__name__}") from exc
        finally:
            _last_call = time.monotonic()
    return parse_results(data if isinstance(data, list) else [])


async def resolve_center(name: str) -> tuple[float, float, str] | None:
    name = clean_query(name)
    if not name:
        return None
    if name in CITY_CENTERS:
        lat, lon = CITY_CENTERS[name]
        return lat, lon, name
    found = await search_places(name, lang="ru", limit=1)
    if not found:
        found = await search_places(name, lang="en", limit=1)
    if not found:
        return None
    top = found[0]
    return top["lat"], top["lon"], top["label"]


LODGING_QUERIES = ("hotel", "hostel", "guest house", "apartment")
LODGING_KINDS = {"hotel", "hostel", "guest_house", "apartment", "motel", "chalet"}


async def _ask_lodging(query: str, box: tuple[float, float, float, float]) -> list[dict]:
    global _last_call
    west, north, east, south = box
    params = {
        "q": query,
        "format": "jsonv2",
        "limit": 40,
        "addressdetails": 1,
        "extratags": 1,
        "bounded": 1,
        "viewbox": f"{west:.5f},{north:.5f},{east:.5f},{south:.5f}",
    }
    async with _lock:
        wait = MIN_GAP - (time.monotonic() - _last_call)
        if wait > 0:
            await asyncio.sleep(wait)
        try:
            async with httpx.AsyncClient(timeout=12, headers=HEADERS) as client:
                resp = await client.get(NOMINATIM_URL, params=params)
                resp.raise_for_status()
                data = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise GeocodeError(f"Nominatim: {type(exc).__name__}") from exc
        finally:
            _last_call = time.monotonic()
    return data if isinstance(data, list) else []


def lodging_to_element(item: dict) -> dict | None:
    kind = item.get("type")
    if item.get("category") != "tourism" or kind not in LODGING_KINDS:
        return None
    name = item.get("name") or ""
    try:
        lat, lon = float(item["lat"]), float(item["lon"])
        osm_id = int(item["osm_id"])
    except (KeyError, TypeError, ValueError):
        return None
    osm_type = item.get("osm_type")
    if not name or osm_type not in ("node", "way", "relation"):
        return None
    address = item.get("address") or {}
    tags = {**(item.get("extratags") or {}), "name": name, "tourism": kind}
    if address.get("road"):
        tags["addr:street"] = address["road"]
    if address.get("house_number"):
        tags["addr:housenumber"] = address["house_number"]
    return {"type": osm_type, "id": osm_id, "lat": lat, "lon": lon, "center": {"lat": lat, "lon": lon}, "tags": tags}


async def search_lodging(lat: float, lon: float, radius_m: int = 4000) -> list[dict]:
    dlat = radius_m / 111000
    dlon = radius_m / (111000 * max(0.2, abs(math.cos(math.radians(lat)))))
    box = (lon - dlon, lat + dlat, lon + dlon, lat - dlat)
    seen: dict[tuple, dict] = {}
    for query in LODGING_QUERIES:
        for item in await _ask_lodging(query, box):
            element = lodging_to_element(item)
            if element:
                seen[(element["type"], element["id"])] = element
    return list(seen.values())
