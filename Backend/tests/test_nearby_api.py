from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import nearby_routes
from app.api.auth import current_user
from app.providers import registry
from app.providers.base import ProviderUnavailable


class FakePlaces:
    name = "fake"

    def __init__(self, error=False):
        self.error = error
        self.calls = []

    async def search(self, category, lat, lon, radius=1000, **options):
        self.calls.append((category, round(lat, 3), round(lon, 3), radius, options))
        if self.error:
            raise ProviderUnavailable("down")
        return {"category": category, "radius": radius, "total": 1, "offline": False,
                "items": [{"id": "n1", "name": "Кафе", "distance_m": 100}]}


def make_client(monkeypatch, places):
    async def fake_profile(telegram_id):
        return {"food_prefs": ["vegan"], "accessible": True, "with_pets": False}

    monkeypatch.setattr(nearby_routes, "get_profile", fake_profile)
    registry.override("places", places)
    app = FastAPI()
    app.include_router(nearby_routes.router)
    app.dependency_overrides[current_user] = lambda: {"id": 1}
    return TestClient(app)


def test_city_request_uses_city_center_and_profile(monkeypatch):
    places = FakePlaces()
    client = make_client(monkeypatch, places)
    r = client.get("/api/nearby", params={"category": "food", "city": "Казань", "radius": 2000})
    assert r.status_code == 200
    body = r.json()
    assert body["items"][0]["name"] == "Кафе"
    assert body["center"]["city"] == "Казань"
    category, lat, lon, radius, options = places.calls[0]
    assert (category, lat, lon, radius) == ("food", 55.789, 49.122, 2000)
    assert options == {"food_prefs": ["vegan"], "accessible": True, "with_pets": False}


def test_validation(monkeypatch):
    client = make_client(monkeypatch, FakePlaces())
    assert client.get("/api/nearby", params={"category": "zzz", "city": "Казань"}).status_code == 400
    assert client.get("/api/nearby", params={"city": "Атлантида"}).status_code == 400
    assert client.get("/api/nearby").status_code == 400                                   # нет места
    assert client.get("/api/nearby", params={"lat": 48.85, "lon": 2.35}).status_code == 400  # Париж, не Россия


def test_unavailable_source_gives_503(monkeypatch):
    client = make_client(monkeypatch, FakePlaces(error=True))
    assert client.get("/api/nearby", params={"city": "Казань"}).status_code == 503


def test_offline_note(monkeypatch):
    class Offline(FakePlaces):
        async def search(self, *a, **k):
            r = await super().search(*a, **k)
            r["offline"] = True
            return r

    client = make_client(monkeypatch, Offline())
    body = client.get("/api/nearby", params={"city": "Казань"}).json()
    assert "сохранённая копия" in body["note"]
