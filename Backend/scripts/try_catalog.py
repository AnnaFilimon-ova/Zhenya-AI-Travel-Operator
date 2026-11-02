import asyncio
import sys

from app.catalog import list_cities, search_catalog


async def main() -> None:
    cities = await list_cities()
    print("В каталоге:", ", ".join(f"{c['city']} ({c['count']})" for c in cities))

    if len(sys.argv) < 2:
        return
    city = sys.argv[1]
    min_stars = int(sys.argv[2]) if len(sys.argv) > 2 else None

    result = await search_catalog(city, min_stars=min_stars, limit=5)
    print(f"\n{city}: найдено {result['total_found']}, показываю {len(result['hotels'])}")
    for hotel in result["hotels"]:
        stars = f"{hotel['stars']}*" if hotel["stars"] else "-"
        print(
            f"- {hotel['name']} [{hotel['kind_label']}, {stars}] "
            f"{hotel['address'] or 'адрес не указан'} | "
            f"питомцы: {hotel['pets']}, доступность: {hotel['wheelchair']} | "
            f"{hotel['website'] or 'сайта нет'}"
        )


if __name__ == "__main__":
    asyncio.run(main())