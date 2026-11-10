import asyncio
import threading
from datetime import date, timedelta

import httpx
import pytest

from app import iata
from app.geo import resolve_iata
from app.providers import registry, transport
from app.providers.base import ProviderUnavailable
from app.providers.transport import NoTransport, TravelpayoutsFlights, compare

SECRET = "super-secret-token"
FUTURE = (date.today() + timedelta(days=30)).isoformat()
ROWS = [
    {"origin": "MOW", "destination": "LED", "depart_date": FUTURE, "value": 5200, "number_of_changes": 1,
     "duration": 190, "found_at": "2026-10-26T10:00:00", "actual": True},
    {"origin": "MOW", "destination": "LED", "depart_date": FUTURE, "value": 3100, "number_of_changes": 0,
     "duration": 90, "actual": True},
    {"origin": "MOW", "destination": "LED", "depart_date": FUTURE, "value": None},
    {"origin": "MOW", "destination": "LED", "depart_date": FUTURE, "value": 9900, "number_of_changes": 2},
]


@pytest.fixture(autouse=True)
def clean_iata_cache(monkeypatch):
    monkeypatch.setattr(iata, "_cache", {})


def mock_http(monkeypatch, handler):
    real = httpx.AsyncClient

    def factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real(*args, **kwargs)

    monkeypatch.setattr(transport.httpx, "AsyncClient", factory)


def ok(rows):
    return lambda request: httpx.Response(200, json={"success": True, "data": rows})


def test_resolve_iata():
    assert resolve_iata("Москва") == "MOW"
    assert resolve_iata("kzn") == "KZN"
    assert resolve_iata("Атлантида") is None
    assert resolve_iata("") is None


def test_search_sorts_filters_and_formats(monkeypatch):
    seen = {}

    def handler(request):
        seen.update(dict(request.url.params))
        return httpx.Response(200, json={"success": True, "data": ROWS})

    mock_http(monkeypatch, handler)
    res = asyncio.run(TravelpayoutsFlights(SECRET).search("Москва", "Санкт-Петербург", FUTURE, max_price=6000))
    assert [o["price_rub"] for o in res["options"]] == [3100, 5200]
    first = res["options"][0]
    assert first["mode"] == "plane" and first["transfers"] == 0 and first["duration_min"] == 90
    assert first["url"].startswith("https://www.aviasales.ru/search/MOW") and first["number"] is None
    assert res["estimate"] is True and "кэш" in res["note"]
    assert seen["origin"] == "MOW" and seen["destination"] == "LED"
    assert seen["period_type"] == "day" and seen["beginning_of_period"] == FUTURE
    assert res["comparison"]["cheapest_id"] == first["id"]
    assert res["comparison"]["fastest_id"] == first["id"]


def test_worldwide_city_names(monkeypatch):
    seen = {}

    def handler(request):
        seen.update(dict(request.url.params))
        return httpx.Response(200, json={"success": True, "data": [{"depart_date": FUTURE, "value": 12000}]})

    mock_http(monkeypatch, handler)
    res = asyncio.run(TravelpayoutsFlights(SECRET).search("Москва", "Тбилиси", FUTURE))
    assert seen["destination"] == "TBS" and res["options"][0]["destination"] == "TBS"
    assert res["options"][0]["url"].endswith("TBS1")


def test_unknown_city_uses_autocomplete(monkeypatch):
    def handler(request):
        if request.url.host == "autocomplete.travelpayouts.com":
            return httpx.Response(200, json=[{"code": "XYZ", "name": "Невидимка"}])
        assert request.url.params["destination"] == "XYZ"
        return httpx.Response(200, json={"success": True, "data": [{"depart_date": FUTURE, "value": 1000}]})

    mock_http(monkeypatch, handler)
    res = asyncio.run(TravelpayoutsFlights(SECRET).search("Москва", "Невидимка", FUTURE))
    assert res["options"][0]["price_rub"] == 1000


def test_limit_five_options(monkeypatch):
    rows = [{"depart_date": FUTURE, "value": 1000 + i} for i in range(9)]
    mock_http(monkeypatch, ok(rows))
    res = asyncio.run(TravelpayoutsFlights(SECRET).search("MOW", "AER"))
    assert len(res["options"]) == 5 and res["options"][0]["price_rub"] == 1000


@pytest.mark.parametrize(
    "args",
    [("Москва", "Москва", ""), ("Москва", "Сочи", "вчера"), ("Москва", "Сочи", "2020-01-01")],
)
def test_bad_input_returns_empty_without_calling_api(monkeypatch, args):
    def boom(request):
        raise AssertionError("API must not be called")

    mock_http(monkeypatch, boom)
    res = asyncio.run(TravelpayoutsFlights(SECRET).search(*args))
    assert res["options"] == [] and res["note"]


def test_unresolved_city_does_not_call_flights_api(monkeypatch):
    def handler(request):
        assert request.url.host == "autocomplete.travelpayouts.com"
        return httpx.Response(200, json=[])

    mock_http(monkeypatch, handler)
    res = asyncio.run(TravelpayoutsFlights(SECRET).search("Атлантида", "Москва", ""))
    assert res["options"] == [] and res["note"]


def test_trains_are_not_connected(monkeypatch):
    mock_http(monkeypatch, ok(ROWS))
    res = asyncio.run(TravelpayoutsFlights(SECRET).search("Москва", "Сочи", mode="train"))
    assert res["options"] == [] and "авиабилеты" in res["note"]


def test_http_error_does_not_leak_token(monkeypatch, caplog):
    mock_http(monkeypatch, lambda request: httpx.Response(500))
    with caplog.at_level("WARNING"), pytest.raises(ProviderUnavailable) as exc:
        asyncio.run(TravelpayoutsFlights(SECRET).search("Москва", "Сочи"))
    assert SECRET not in str(exc.value) and SECRET not in caplog.text


def test_api_error_payload_is_unavailable(monkeypatch):
    mock_http(monkeypatch, lambda request: httpx.Response(200, json={"success": False, "error": "bad token"}))
    with pytest.raises(ProviderUnavailable):
        asyncio.run(TravelpayoutsFlights(SECRET).search("Москва", "Сочи"))


def test_registry_picks_provider_by_key(monkeypatch):
    monkeypatch.setattr("app.providers.registry.settings.avia_api_key", "")
    assert isinstance(registry.get_transport(), NoTransport)
    monkeypatch.setattr("app.providers.registry.settings.avia_api_key", SECRET)
    assert isinstance(registry.get_transport(), TravelpayoutsFlights)


def test_no_transport_is_honest():
    res = asyncio.run(NoTransport().search("Москва", "Сочи", ""))
    assert res["options"] == [] and "не подключён" in res["note"]


def test_agent_tool(monkeypatch):
    pytest.importorskip("google.genai")
    from app.agent import service

    class Fake:
        name = "fake"
        called = None

        async def search(self, origin, destination, date="", **options):
            Fake.called = (origin, destination, date, options)
            return {"source": "fake", "estimate": True, "note": "", "options": [{"price_rub": 1}]}

    class Down:
        name = "down"

        async def search(self, *a, **k):
            raise ProviderUnavailable("x")

    loop = asyncio.new_event_loop()
    threading.Thread(target=loop.run_forever, daemon=True).start()
    service._loop = loop
    try:
        registry.override("transport", Fake())
        out = service.search_transport_for_agent("Москва", "Сочи", FUTURE, 8000)
        assert out["options"] == [{"price_rub": 1}]
        assert Fake.called == ("Москва", "Сочи", FUTURE, {"max_price": 8000, "mode": "any"})
        service.search_transport_for_agent("Москва", "Сочи")
        assert Fake.called[3] == {"max_price": None, "mode": "any"}
        assert "error" in service.search_transport_for_agent("Москва", "Сочи", mode="train")
        registry.override("transport", Down())
        assert service.search_transport_for_agent("Москва", "Сочи")["options"] == []
    finally:
        registry.reset()
        service._loop = None
        loop.call_soon_threadsafe(loop.stop)


def plane(price, minutes, oid="p"):
    return {"id": oid, "mode": "plane", "price_rub": price, "duration_min": minutes}


def test_compare_cheapest_and_fastest():
    res = compare([plane(6000, 230, "a"), plane(3500, 400, "b"), {"id": "c", "mode": "plane", "price_rub": 9000}])
    assert res["cheapest_id"] == "b" and res["fastest_id"] == "a"


def test_compare_without_durations_and_empty():
    assert compare([{"id": "x", "mode": "plane", "price_rub": 100}])["fastest_id"] is None
    assert compare([]) is None


def test_flights_carry_aviasales_link(monkeypatch):
    mock_http(monkeypatch, ok([{"origin": "MOW", "destination": "LED", "depart_date": "2030-01-15T09:00:00+03:00", "value": 4000}]))
    res = asyncio.run(TravelpayoutsFlights(SECRET).search("Москва", "Санкт-Петербург"))
    assert res["options"][0]["url"] == "https://www.aviasales.ru/search/MOW1501LED1"
