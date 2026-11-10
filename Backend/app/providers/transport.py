import logging
from datetime import date as date_cls

import httpx

from app.iata import resolve_iata_world
from app.providers.base import ProviderUnavailable

log = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

API_URL = "https://api.travelpayouts.com/aviasales/v3/get_latest_prices"
MAX_OPTIONS = 5
NOTE = (
    "Цены из кэша Aviasales: это недавно найденные другими пользователями предложения, "
    "они могут измениться или быть уже недоступны. Купить билет здесь нельзя."
)


class NoTransport:
    name = "none"

    async def search(self, origin: str, destination: str, date: str = "", **options) -> dict:
        return {
            "source": self.name,
            "estimate": True,
            "note": "Поиск транспорта пока не подключён.",
            "options": [],
        }


def _empty(note: str) -> dict:
    return {"source": "travelpayouts", "estimate": True, "note": note, "options": []}


def flight_link(origin: str, destination: str, depart: str | None) -> str:
    if not depart or len(depart) < 10 or depart[4] != "-" or depart[7] != "-":
        return ""
    return f"https://www.aviasales.ru/search/{origin}{depart[8:10]}{depart[5:7]}{destination}1"


def to_option(row: dict, origin: str, destination: str) -> dict | None:
    price = row.get("value")
    if not isinstance(price, (int, float)) or isinstance(price, bool):
        return None
    depart = row.get("depart_date")
    return {
        "id": f"{origin}-{destination}-{depart}-{round(price)}",
        "mode": "plane",
        "origin": row.get("origin") or origin,
        "destination": row.get("destination") or destination,
        "depart_at": depart,
        "arrive_at": None,
        "duration_min": row.get("duration"),
        "price_rub": round(price),
        "carrier": None,
        "number": None,
        "url": flight_link(row.get("origin") or origin, row.get("destination") or destination, depart),
        "transfers": row.get("number_of_changes"),
        "found_at": row.get("found_at"),
        "actual": row.get("actual"),
    }


class TravelpayoutsFlights:
    name = "travelpayouts"

    def __init__(self, api_key: str):
        self._key = api_key

    async def search(
        self,
        origin: str,
        destination: str,
        date: str = "",
        *,
        mode: str = "any",
        adults: int = 1,
        max_price: int | None = None,
    ) -> dict:
        if mode not in ("any", "plane"):
            return _empty("Подключены только авиабилеты.")
        o, d = await resolve_iata_world(origin), await resolve_iata_world(destination)
        if not o or not d:
            return _empty(
                "Не удалось определить город вылета или прилёта. Уточни название города "
                "или назови трёхбуквенный код аэропорта."
            )
        if o == d:
            return _empty("Город вылета и прилёта совпадают.")

        params = {
            "origin": o,
            "destination": d,
            "currency": "rub",
            "market": "ru",
            "sorting": "price",
            "one_way": "true",
            "page": 1,
            "token": self._key,
        }
        if date:
            try:
                day = date_cls.fromisoformat(date)
            except ValueError:
                return _empty("Дата должна быть в формате ГГГГ-ММ-ДД.")
            if day < date_cls.today():
                return _empty("Эта дата уже прошла.")
            params["period_type"] = "day"
            params["beginning_of_period"] = day.isoformat()

        rows = await self._fetch(params)
        options = [x for x in (to_option(r, o, d) for r in rows) if x]
        if max_price:
            options = [x for x in options if x["price_rub"] <= max_price]
        options.sort(key=lambda x: x["price_rub"])
        note = NOTE if options else NOTE + " По этому маршруту и условиям предложений не нашлось."
        return {
            "source": self.name,
            "estimate": True,
            "note": note,
            "options": options[:MAX_OPTIONS],
            "comparison": compare(options),
        }

    async def _fetch(self, params: dict) -> list[dict]:
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.get(API_URL, params=params)
                resp.raise_for_status()
                data = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            log.warning("Travelpayouts request failed: %s", type(exc).__name__)
            raise ProviderUnavailable("flight source unavailable") from None
        if not isinstance(data, dict) or not data.get("success", False) or not isinstance(data.get("data"), list):
            log.warning("Travelpayouts returned an unexpected response")
            raise ProviderUnavailable("flight source returned an error")
        return data["data"]


def compare(options: list[dict]) -> dict | None:
    if not options:
        return None
    cheapest = min(options, key=lambda o: o["price_rub"])
    timed = [o for o in options if isinstance(o.get("duration_min"), (int, float))]
    fastest = min(timed, key=lambda o: o["duration_min"]) if timed else None
    return {"cheapest_id": cheapest["id"], "fastest_id": fastest["id"] if fastest else None}
