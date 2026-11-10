import asyncio
import threading

import pytest

from app import nearby
from app.city_places import places_in_city
from app.interests import TRAVEL_TO_PLACES, suggested_categories
from app.providers import registry
from app.providers.base import ProviderUnavailable


def run(coro):
    return asyncio.run(coro)


def test_every_travel_type_has_existing_categories():
    from app.api.main import TRAVEL_TYPES

    assert set(TRAVEL_TO_PLACES) == set(TRAVEL_TYPES)
    for categories in TRAVEL_TO_PLACES.values():
        assert categories and all(c in nearby.CATEGORIES for c in categories)


def test_urbex_is_replaced_by_gothic():
    from app.api.main import TRAVEL_TYPES
    from app.profile import normalize_travel

    assert "urbex" not in TRAVEL_TYPES and "gothic" in TRAVEL_TYPES
    assert normalize_travel(["urbex", "beach"]) == ["beach", "gothic"]
    assert normalize_travel(["gothic", "urbex"]) == ["gothic"]


def test_suggested_categories_keep_order_and_have_no_duplicates():
    assert suggested_categories(["gothic", "city", "aesthetic"]) == ["gothic", "sights", "nature"]
    assert suggested_categories(["nonsense"]) == []


def test_gothic_query_has_cathedrals_castles_and_cemeteries_but_not_abandoned():
    q = nearby.build_query("gothic", 55.75, 37.62, 2000)
    assert '["building"="cathedral"]' in q
    assert '["historic"="castle"]' in q and '["historic"="cemetery"]' in q
    assert "ruins" not in q and "abandoned" not in q


def test_kind_labels_for_gothic_objects():
    assert nearby._kind({"building": "cathedral", "amenity": "place_of_worship"}) == "собор"
    assert nearby._kind({"historic": "cemetery"}) == "историческое кладбище"
    assert nearby._kind({"building:architecture": "gothic_revival"}) == "здание в готическом стиле"
    assert nearby._kind({"shop": "mall"}) == "торговый центр"


def test_cathedral_is_returned_with_address_and_distance():
    els = [{"type": "way", "id": 1, "center": {"lat": 55.7512, "lon": 37.6184},
            "tags": {"name": "Собор", "building": "cathedral", "addr:street": "Тверская", "addr:housenumber": "1"}}]
    item = nearby.parse_elements(els, 55.7558, 37.6173, [], False, False)[0]
    assert item["kind"] == "собор" and item["address"] == "Тверская, 1" and item["distance_m"] > 0


class FakePlaces:
    name = "fake"

    def __init__(self, error=False):
        self.error, self.calls = error, []

    async def search(self, category, lat, lon, radius=1000, **options):
        self.calls.append((category, round(lat, 2), round(lon, 2), radius, options.get("limit")))
        if self.error:
            raise ProviderUnavailable("down")
        item = {"name": "Собор", "kind": "собор", "address": "", "distance_m": 120, "cuisine": "",
                "badges": [{"text": "доступно на коляске", "match": False}], "website": ""}
        return {"total": 25, "items": [item], "offline": True}


def test_city_places_for_agent():
    fake = FakePlaces()
    registry.override("places", fake)
    result = run(places_in_city("Москва", "gothic", limit=50))
    assert fake.calls == [("gothic", 55.76, 37.62, 2000, 10)]
    place = result["places"][0]
    assert place["name"] == "Собор" and place["notes"] == ["доступно на коляске"]
    assert result["total_found"] == 25 and "сохранённая копия" in result["note"]


def test_city_places_errors_are_explained_to_the_agent(monkeypatch):
    from app import city_places

    async def not_found(name):
        return None

    monkeypatch.setattr(city_places, "resolve_center", not_found)
    registry.override("places", FakePlaces())
    assert "error" in run(places_in_city("Атлантида", "gothic"))
    assert "categories" in run(places_in_city("Москва", "zzz"))
    registry.override("places", FakePlaces(error=True))
    assert run(places_in_city("Москва", "gothic"))["places"] == []


def test_city_places_work_for_any_city_in_the_world(monkeypatch):
    from app import city_places

    async def paris(name):
        return (48.8566, 2.3522, "Париж, Франция")

    monkeypatch.setattr(city_places, "resolve_center", paris)
    fake = FakePlaces()
    registry.override("places", fake)
    result = run(places_in_city("Paris", "sights"))
    assert result["city"] == "Париж, Франция" and fake.calls[0][1:3] == (48.86, 2.35)


def test_agent_tool_wrapper():
    pytest.importorskip("google.genai")
    from app.agent import service

    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=loop.run_forever, daemon=True)
    thread.start()
    service._loop = loop
    try:
        registry.override("places", FakePlaces())
        result = service.places_for_agent("Москва", "gothic")
        assert result["places"][0]["name"] == "Собор"
    finally:
        loop.call_soon_threadsafe(loop.stop)
        thread.join(timeout=2)
        service._loop = None


def test_categories_endpoint_puts_suggested_first(monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.api import nearby_routes
    from app.api.auth import current_user

    async def fake_profile(telegram_id):
        return {"travel_types": ["gothic", "beach"]}

    monkeypatch.setattr(nearby_routes, "get_profile", fake_profile)
    app = FastAPI()
    app.include_router(nearby_routes.router)
    app.dependency_overrides[current_user] = lambda: {"id": 1}
    body = TestClient(app).get("/api/nearby/categories").json()
    keys = [c["key"] for c in body["categories"]]
    assert keys[:2] == ["gothic", "beach"] and set(keys) == set(nearby.CATEGORIES)
    assert [c["suggested"] for c in body["categories"][:3]] == [True, True, False]
    assert next(c for c in body["categories"] if c["key"] == "gothic")["label"] == "Готика"


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self.payload


class FakeClient:
    def __init__(self, payload):
        self.payload = payload

    async def post(self, url, data):
        return FakeResponse(self.payload)


def test_overloaded_overpass_answer_is_rejected():
    overloaded = {"elements": [], "remark": "runtime error: Query timed out in \"query\" at line 3."}
    with pytest.raises(ProviderUnavailable):
        run(nearby._ask(FakeClient(overloaded), "https://x", "q"))
    ok = {"elements": [{"id": 1}]}
    assert run(nearby._ask(FakeClient(ok), "https://x", "q")) == [{"id": 1}]
    assert run(nearby._ask(FakeClient({"elements": []}), "https://x", "q")) == []
