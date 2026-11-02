import asyncio
import logging
from datetime import date as date_cls

import httpx

from app.geo import CITY_CENTERS, resolve_city, resolve_iata
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
            return _empty("Подключены только авиабилеты: поезда и автобусы пока недоступны.")
        o, d = resolve_iata(origin), resolve_iata(destination)
        if not o or not d:
            return _empty(
                "Не удалось определить город вылета или прилёта. Нужны название города "
                "из каталога или трёхбуквенный код аэропорта/города."
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
        return {"source": self.name, "estimate": True, "note": note, "options": options[:MAX_OPTIONS]}

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


RAIL_DETOUR = 1.25
RAIL_SPEED_KMH = 75
RAIL_CLASSES = (("platzkart", "плацкарт", 1.9, 400), ("coupe", "купе", 3.6, 700))
PLANE_OVERHEAD_MIN = 180
TRAIN_OVERHEAD_MIN = 60


def _round_to(value: float, step: int) -> int:
    return int(round(value / step) * step)


class MockTrains:
    name = "mock_rail"

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
        note = (
            "Поезда: демонстрационные данные. Время и цена рассчитаны по расстоянию между "
            "городами, это не расписание и не реальные тарифы."
        )
        if mode not in ("any", "train"):
            return {"source": self.name, "estimate": True, "note": note, "options": []}
        a, b = resolve_city(origin), resolve_city(destination)
        if not a or not b or a == b:
            return {"source": self.name, "estimate": True, "note": note, "options": []}
        from app.nearby import distance_m

        straight_km = distance_m(*CITY_CENTERS[a], *CITY_CENTERS[b]) / 1000
        rail_km = straight_km * RAIL_DETOUR
        duration = _round_to(rail_km / RAIL_SPEED_KMH * 60, 5)
        options = []
        for key, label, per_km, base in RAIL_CLASSES:
            price = _round_to(rail_km * per_km + base, 10)
            if max_price and price > max_price:
                continue
            options.append(
                {
                    "id": f"train-{a}-{b}-{key}",
                    "mode": "train",
                    "origin": a,
                    "destination": b,
                    "depart_at": date or None,
                    "arrive_at": None,
                    "duration_min": duration,
                    "price_rub": price,
                    "carrier": None,
                    "number": None,
                    "url": "",
                    "transfers": 0,
                    "car_class": label,
                    "car_key": key,
                    "found_at": None,
                    "actual": None,
                }
            )
        return {"source": self.name, "estimate": True, "note": note, "options": options}


def compare(options: list[dict]) -> dict | None:
    planes = [o for o in options if o["mode"] == "plane"]
    trains = [o for o in options if o["mode"] == "train"]
    if not planes and not trains:
        return None

    def effective(option: dict) -> int | None:
        if not isinstance(option.get("duration_min"), (int, float)):
            return None
        return int(option["duration_min"]) + (PLANE_OVERHEAD_MIN if option["mode"] == "plane" else TRAIN_OVERHEAD_MIN)

    cheapest = min(options, key=lambda o: o["price_rub"])
    timed = [o for o in options if effective(o) is not None]
    fastest = min(timed, key=effective) if timed else None
    result = {
        "cheapest_id": cheapest["id"],
        "fastest_id": fastest["id"] if fastest else None,
        "overhead_note": "В сравнении к самолёту добавлено 3 часа на дорогу до аэропорта и регистрацию, к поезду 1 час.",
    }
    if not planes or not trains:
        only = "plane" if planes else "train"
        result.update(recommended_mode=only, reason="only_option")
        return result
    best_plane = min(planes, key=lambda o: o["price_rub"])
    best_train = min(trains, key=lambda o: o["price_rub"])
    plane_time, train_time = effective(best_plane), effective(best_train)
    price_diff = best_plane["price_rub"] - best_train["price_rub"]
    result.update(price_diff_plane_minus_train_rub=price_diff)
    if plane_time is None or train_time is None:
        result.update(recommended_mode="plane" if price_diff <= 0 else "train", reason="cheaper")
        return result
    saved = train_time - plane_time
    result.update(time_saved_by_plane_min=saved)
    if price_diff <= 0 and saved >= 0:
        mode, reason = "plane", "cheaper_and_faster"
    elif saved >= 240:
        mode, reason = "plane", "much_faster"
    elif saved >= 120 and price_diff <= 3000:
        mode, reason = "plane", "faster_for_small_extra"
    else:
        mode, reason = "train", "cheaper_and_close_in_time"
    result.update(recommended_mode=mode, reason=reason)
    return result


class CombinedTransport:
    name = "combined"

    def __init__(self, flights: "TravelpayoutsFlights | None", trains: MockTrains):
        self._flights = flights
        self._trains = trains

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
        notes: list[str] = []
        kwargs = dict(mode=mode, adults=adults, max_price=max_price)

        async def flights() -> dict | None:
            if mode not in ("any", "plane"):
                return None
            if self._flights is None:
                notes.append("Авиабилеты не подключены.")
                return None
            try:
                return await self._flights.search(origin, destination, date, **kwargs)
            except ProviderUnavailable:
                notes.append("Данные по авиабилетам сейчас недоступны.")
                return None

        flight_res, train_res = await asyncio.gather(
            flights(), self._trains.search(origin, destination, date, **kwargs)
        )
        options: list[dict] = []
        if flight_res and mode == "any":
            flight_res["options"] = flight_res["options"][:3]
        for res in (flight_res, train_res):
            if res:
                options.extend(res["options"])
                if res["note"] and res["note"] not in notes:
                    notes.append(res["note"])
        if not options and not notes:
            notes.append("Вариантов не нашлось.")
        return {
            "source": self.name,
            "estimate": True,
            "note": " ".join(notes),
            "options": options,
            "comparison": compare(options),
        }
