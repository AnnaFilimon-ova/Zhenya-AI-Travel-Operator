import asyncio
import re
import sys

import httpx
from sqlalchemy.dialects.postgresql import insert

from app.db import SessionLocal
from app.models import Hotel

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
HEADERS = {"User-Agent": "ZhenyaTravelBot/0.1 (hackathon project)"}
DEFAULT_CITIES = ["Казань", "Сочи", "Санкт-Петербург"]
KINDS = "hotel|hostel|guest_house|apartment|motel|chalet"


def build_queries(city: str) -> list[str]:
    body = f'nwr["tourism"~"^({KINDS})$"]["name"](area.a);'
    areas = [
        f'area["name"~"^((городской округ|муниципальное образование|город) )?{city}( городской округ)?$"]'
        f'["boundary"="administrative"]->.a;',
        f'area["name"="{city}"]->.a;',
    ]
    return [
        f"[out:json][timeout:180];\n{area}\n(\n  {body}\n);\nout center tags;"
        for area in areas
    ]


def parse_stars(value: str | None) -> int | None:
    if not value:
        return None
    match = re.match(r"\s*([1-5])", value)
    return int(match.group(1)) if match else None


def parse_yes_no(tags: dict, *keys: str) -> bool | None:
    for key in keys:
        value = (tags.get(key) or "").lower()
        if value in ("yes", "true", "1"):
            return True
        if value in ("no", "false", "0"):
            return False
    return None


NO_PETS = re.compile(
    r"(без\s+(животных|питомцев|собак)|(животн\w*|питомц\w*|собак\w*)\s+(нельзя|запрещ\w*|не\s+принима\w*)"
    r"|no\s+pets?|pets?\s+not\s+allowed|not\s+pet[- ]friendly)",
    re.IGNORECASE,
)
YES_PETS = re.compile(
    r"(с\s+(животными|питомцами|собаками|кошками)|(животн\w*|питомц\w*)\s+(разрешен\w*|можно|принима\w*)"
    r"|pet[- ]friendly|pets?\s+(allowed|welcome)|dogs?\s+(allowed|welcome))",
    re.IGNORECASE,
)


def parse_pets(tags: dict) -> bool | None:
    value = parse_yes_no(tags, "pets", "dog", "pets_allowed", "pet")
    if value is not None:
        return value
    text = " ".join(
        str(tags.get(key) or "")
        for key in ("description", "description:ru", "description:en", "note", "note:ru")
    )
    if not text.strip():
        return None
    if NO_PETS.search(text):
        return False
    if YES_PETS.search(text):
        return True
    return None


def element_to_row(element: dict, city: str) -> dict | None:
    tags = element.get("tags") or {}
    name = (tags.get("name") or "").strip()
    if not name:
        return None

    if element["type"] == "node":
        lat, lon = element.get("lat"), element.get("lon")
    else:
        center = element.get("center") or {}
        lat, lon = center.get("lat"), center.get("lon")
    if lat is None or lon is None:
        return None

    street = tags.get("addr:street")
    house = tags.get("addr:housenumber")
    address = ", ".join(part for part in (street, house) if part) or None

    return {
        "osm_type": element["type"],
        "osm_id": element["id"],
        "name": name,
        "kind": tags.get("tourism", "hotel"),
        "city": city,
        "address": address,
        "lat": lat,
        "lon": lon,
        "stars": parse_stars(tags.get("stars")),
        "website": tags.get("website") or tags.get("contact:website"),
        "phone": tags.get("phone") or tags.get("contact:phone"),
        "wheelchair": tags.get("wheelchair"),
        "pets": parse_pets(tags),
        "tags": tags,
    }


async def fetch_city(client: httpx.AsyncClient, city: str) -> list[dict]:
    for query in build_queries(city):
        response = await client.post(OVERPASS_URL, data={"data": query})
        response.raise_for_status()
        elements = response.json().get("elements", [])
        rows = [row for el in elements if (row := element_to_row(el, city))]
        if rows:
            return rows
        await asyncio.sleep(3)
    return []


async def save_rows(rows: list[dict]) -> None:
    if not rows:
        return
    async with SessionLocal() as session:
        stmt = insert(Hotel).values(rows)
        update_cols = {
            col: stmt.excluded[col]
            for col in (
                "name", "kind", "city", "address", "lat", "lon", "stars",
                "website", "phone", "wheelchair", "pets", "tags",
            )
        }
        stmt = stmt.on_conflict_do_update(
            index_elements=["osm_type", "osm_id"], set_=update_cols
        )
        await session.execute(stmt)
        await session.commit()


async def main(cities: list[str]) -> None:
    async with httpx.AsyncClient(timeout=240, headers=HEADERS) as client:
        for city in cities:
            print(f"{city}: загружаю из OpenStreetMap...")
            try:
                rows = await fetch_city(client, city)
            except httpx.HTTPError as error:
                print(f"{city}: ошибка запроса: {error}")
                continue
            await save_rows(rows)
            stars = sum(1 for r in rows if r["stars"])
            pets = sum(1 for r in rows if r["pets"] is not None)
            wheel = sum(1 for r in rows if r["wheelchair"])
            print(
                f"{city}: сохранено {len(rows)} "
                f"(со звёздами: {stars}, с данными о питомцах: {pets}, "
                f"с данными о доступности: {wheel})"
            )
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:] or DEFAULT_CITIES))