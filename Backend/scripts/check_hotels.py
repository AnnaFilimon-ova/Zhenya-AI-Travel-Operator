import asyncio
import json
import sys

from app.hotels_world import search_near


async def main() -> None:
    city = sys.argv[1]
    near = sys.argv[2] if len(sys.argv) > 2 else ""
    result = await search_near(city, near_place=near, limit=5)
    for key in ("city", "near", "near_found", "searched_around", "total_found", "error"):
        print(key, "=", result.get(key))
    for hotel in result["hotels"]:
        print(json.dumps({k: hotel[k] for k in ("name", "kind", "address", "distance_to_place_m", "lat", "lon")}, ensure_ascii=False))


asyncio.run(main())
