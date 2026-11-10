import asyncio
import threading
from datetime import date, timedelta

import pytest

pytest.importorskip("google.genai")

from app import overview  
from app.agent import service  
from app.providers import registry  
from app.providers.base import ProviderUnavailable  


class FakeHotels:
    name = "fake"

    async def search(self, city, **filters):
        prices = {"Сочи": [5000, 7000, 9000], "Казань": [3000, 4000]}[city]
        return {"city": city, "total_found": 100,
                "hotels": [{"id": i, "price_per_night_est": p} for i, p in enumerate(prices)], "note": ""}

    async def cities(self):
        return []


class FakeWeather:
    name = "fake"

    def __init__(self, broken=False):
        self.broken, self.calls = broken, []

    async def summary(self, lat, lon, start, end):
        self.calls.append((round(lat), round(lon), start, end))
        if self.broken:
            raise ProviderUnavailable("down")
        return {"source": "forecast", "temp_max_avg": 12, "temp_min_avg": 5, "rainy_days": 1}


def run(coro):
    return asyncio.run(coro)


def test_parse_dates_defaults_and_order():
    start, end = overview.parse_dates("", "")
    assert start == date.today() + timedelta(days=7) and end == start + timedelta(days=3)
    assert overview.parse_dates("2026-11-14", "2026-11-10") == (date(2026, 11, 10), date(2026, 11, 14))
    with pytest.raises(ValueError):
        overview.parse_dates("завтра", "")


def test_overview_combines_weather_and_price_per_city(monkeypatch):
    async def not_found(name):
        return None

    monkeypatch.setattr(overview, "resolve_center", not_found)
    weather = FakeWeather()
    registry.override("hotels", FakeHotels())
    registry.override("weather", weather)
    result = run(overview.destination_overview(["Сочи", "Казань", "Сочи", "Атлантида"], "2026-11-10", "2026-11-14"))
    by_city = {c["city"]: c for c in result["cities"]}
    assert list(by_city) == ["Сочи", "Казань", "Атлантида"]
    assert by_city["Сочи"]["typical_price_per_night_est"] == 7000
    assert by_city["Казань"]["typical_price_per_night_est"] == 3500
    assert by_city["Сочи"]["weather"]["temp_max_avg"] == 12
    assert "error" in by_city["Атлантида"]
    assert len(weather.calls) == 2


def test_weather_failure_does_not_break_the_overview():
    registry.override("hotels", FakeHotels())
    registry.override("weather", FakeWeather(broken=True))
    result = run(overview.destination_overview(["Сочи"], "2026-11-10", "2026-11-14"))
    assert result["cities"][0]["weather"] == {"error": "погода сейчас недоступна"}
    assert result["cities"][0]["typical_price_per_night_est"] == 7000


def test_at_most_four_cities():
    registry.override("hotels", FakeHotels())
    registry.override("weather", FakeWeather())
    cities = ["Сочи", "Казань", "Москва", "Рязань", "Иркутск"]

    class Any(FakeHotels):
        async def search(self, city, **filters):
            return {"city": city, "total_found": 1, "hotels": [{"id": 1, "price_per_night_est": 1000}], "note": ""}

    registry.override("hotels", Any())
    assert len(run(overview.destination_overview(cities))["cities"]) == overview.MAX_CITIES


def test_agent_tool_runs_in_main_loop_and_handles_bad_dates():
    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=loop.run_forever, daemon=True)
    thread.start()
    service._loop = loop
    try:
        registry.override("hotels", FakeHotels())
        registry.override("weather", FakeWeather())
        ok = service.destination_overview_for_agent(["Сочи"], "2026-11-10", "2026-11-12")
        assert ok["cities"][0]["city"] == "Сочи"
        bad = service.destination_overview_for_agent(["Сочи"], "не дата", "")
        assert bad["cities"] == [] and "YYYY-MM-DD" in bad["error"]
    finally:
        loop.call_soon_threadsafe(loop.stop)
        thread.join(timeout=2)
        service._loop = None
