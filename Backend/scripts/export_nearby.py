import asyncio
import json
import sys

from app.nearby import (
    CATEGORIES, CITY_CENTERS, SEED_PATH, NearbyError, _is_abandoned, build_query, fetch_overpass,
)

RADIUS = 2000
LIMIT = 400
KEEP = {
    "name", "amenity", "tourism", "historic", "leisure", "natural", "cuisine", "diet:vegan",
    "diet:vegetarian", "diet:halal", "wheelchair", "dog", "pets", "addr:street",
    "addr:housenumber", "website", "contact:website", "opening_hours",
    "building", "building:architecture", "architecture", "shop", "sport",
}


def slim(elements: list[dict]) -> list[dict]:
    out = []
    for el in elements:
        tags = el.get("tags") or {}
        if _is_abandoned(tags):
            continue
        lat = el.get("lat") or (el.get("center") or {}).get("lat")
        lon = el.get("lon") or (el.get("center") or {}).get("lon")
        if lat is None or lon is None:
            continue
        out.append(
            {
                "type": el.get("type", "n"), "id": el.get("id"), "lat": lat, "lon": lon,
                "tags": {k: v for k, v in tags.items() if k in KEEP},
            }
        )
    return out


async def main(cities: list[str]) -> None:
    SEED_PATH.parent.mkdir(parents=True, exist_ok=True)
    seed = json.loads(SEED_PATH.read_text(encoding="utf-8")) if SEED_PATH.exists() else {}
    for city in cities:
        lat, lon = CITY_CENTERS[city]
        for category in CATEGORIES:
            if seed.get(city, {}).get(category):
                continue
            for attempt in range(1, 5):
                try:
                    elements = slim(await fetch_overpass(build_query(category, lat, lon, RADIUS, LIMIT), timeout=60))
                    if not elements and attempt < 3:
                        print(f"{city} / {category}: пусто, перепроверяю (попытка {attempt})")
                        await asyncio.sleep(10 * attempt)
                        continue
                    seed.setdefault(city, {})[category] = elements
                    SEED_PATH.write_text(json.dumps(seed, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
                    print(f"{city} / {category}: {len(seed[city][category])}")
                    break
                except NearbyError:
                    print(f"{city} / {category}: попытка {attempt} не удалась, жду")
                    await asyncio.sleep(10 * attempt)
            else:
                print(f"{city} / {category}: пропущено, запусти скрипт ещё раз позже")
            await asyncio.sleep(2)


if __name__ == "__main__":
    names = sys.argv[1:] or list(CITY_CENTERS)
    unknown = [n for n in names if n not in CITY_CENTERS]
    if unknown:
        sys.exit("Неизвестные города: " + ", ".join(unknown))
    asyncio.run(main(names))
