import asyncio
import sys

from sqlalchemy import func, select, text
from sqlalchemy.engine import make_url

from app.config import settings
from app.db import SessionLocal
from app.models import Hotel
from app.providers.registry import get_hotels


async def main(city: str) -> None:
    print("База:", make_url(settings.database_url).render_as_string(hide_password=True))
    async with SessionLocal() as session:
        total = (await session.execute(select(func.count()).select_from(Hotel))).scalar_one()
        print("Всего отелей в таблице hotels:", total)
        rows = await session.execute(
            select(Hotel.city, func.count()).group_by(Hotel.city).order_by(Hotel.city)
        )
        for name, count in rows.all():
            print(f"  {name!r}: {count}")
        collation = (await session.execute(text("select datcollate from pg_database where datname = current_database()"))).scalar_one()
        print("Локаль базы:", collation)

    hotels = get_hotels()
    result = await hotels.search(city, limit=2)
    print(f"Поиск через провайдера {hotels.name!r} по городу {city!r}: найдено {result['total_found']}")
    for item in result["hotels"]:
        print("  ", item["name"], item["price_per_night_est"])


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "Москва"))
