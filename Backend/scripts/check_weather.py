import asyncio
import sys

from app.overview import destination_overview


async def main(args: list[str]) -> None:
    cities = [a for a in args if not a[:1].isdigit()] or ["Сочи", "Казань"]
    dates = [a for a in args if a[:1].isdigit()]
    result = await destination_overview(cities, *(dates + ["", ""])[:2])
    print("Даты:", result["dates"])
    for item in result["cities"]:
        print(item)


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))
