import asyncio
import threading

import pytest

pytest.importorskip("google.genai")

from app.agent import service  
from app.providers import registry  


class FakeHotels:
    name = "fake"

    def __init__(self, hotels):
        self.hotels = hotels

    async def search(self, city, **filters):
        return {"city": city, "total_found": len(self.hotels), "hotels": self.hotels, "note": ""}

    async def cities(self):
        return [{"city": "Тестоград", "count": 1}, {"city": "Другоград", "count": 2}]


@pytest.fixture
def loop_in_thread():
    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=loop.run_forever, daemon=True)
    thread.start()
    service._loop = loop
    yield loop
    loop.call_soon_threadsafe(loop.stop)
    thread.join(timeout=2)
    service._loop = None


def test_tool_returns_hotels_and_remembers_them_for_buttons(loop_in_thread):
    registry.override("hotels", FakeHotels([{"id": 7, "name": "Тестовый отель", "price_per_night_est": 4700}]))
    service._current_user.set(42)
    result = service.search_catalog_for_agent(city="Москва", limit=5)
    assert result is not None
    assert result["total_found"] == 1
    assert result["hotels"][0]["name"] == "Тестовый отель"
    assert service.pop_offered(42) == [{"id": 7, "name": "Тестовый отель", "price": 4700}]


def test_tool_lists_available_cities_when_nothing_found(loop_in_thread):
    registry.override("hotels", FakeHotels([]))
    service._current_user.set(43)
    result = service.search_catalog_for_agent(city="Нигде")
    assert result["total_found"] == 0
    assert result["available_cities"] == ["Тестоград", "Другоград"]
    assert service.pop_offered(43) == []
