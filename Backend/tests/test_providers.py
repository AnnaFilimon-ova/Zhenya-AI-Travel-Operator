"""Подмена источников данных: остальной код не знает, откуда берутся жильё, места и транспорт."""
import asyncio

from app.providers import registry
from app.providers.base import ProviderUnavailable
from app.providers.hotels import OsmCatalogHotels
from app.providers.places import OverpassPlaces
from app.providers.transport import CombinedTransport, NoTransport


class FakeHotels:
    name = "fake"

    async def search(self, city, **filters):
        return {"city": city, "total_found": 1, "hotels": [{"id": 7, "name": "Тестовый отель"}], "note": ""}

    async def cities(self):
        return [{"city": "Тестоград", "count": 1}]


def test_defaults_are_real_providers(monkeypatch):
    monkeypatch.setattr("app.providers.registry.settings.avia_api_key", "")
    assert isinstance(registry.get_hotels(), OsmCatalogHotels)
    assert isinstance(registry.get_places(), OverpassPlaces)
    assert isinstance(registry.get_transport(), CombinedTransport)


def test_override_replaces_provider_and_reset_restores():
    registry.override("hotels", FakeHotels())
    hotels = registry.get_hotels()
    assert asyncio.run(hotels.search("Тестоград"))["hotels"][0]["name"] == "Тестовый отель"
    assert asyncio.run(hotels.cities()) == [{"city": "Тестоград", "count": 1}]
    registry.reset()
    assert isinstance(registry.get_hotels(), OsmCatalogHotels)


def test_transport_stub_is_honest():
    result = asyncio.run(NoTransport().search("Москва", "Казань", "2026-11-01"))
    assert result["options"] == []
    assert "не подключён" in result["note"]


def test_places_provider_translates_errors(monkeypatch):
    from app import nearby

    async def dead(*args, **kwargs):
        raise nearby.NearbyError("down")

    monkeypatch.setattr(nearby, "search_nearby", dead)
    try:
        asyncio.run(OverpassPlaces().search("food", 55.7, 37.6))
    except ProviderUnavailable:
        pass
    else:
        raise AssertionError("ожидали ProviderUnavailable")
