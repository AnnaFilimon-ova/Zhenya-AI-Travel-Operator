import asyncio
import threading
from datetime import date, timedelta

import httpx
import pytest

from app.geo import resolve_iata
from app.providers import registry, transport
from app.providers.base import ProviderUnavailable
from app.providers.transport import (
    CombinedTransport,
    MockTrains,
    NoTransport,
    TravelpayoutsFlights,
    compare,
)

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


def test_limit_five_options(monkeypatch):
    rows = [{"depart_date": FUTURE, "value": 1000 + i} for i in range(9)]
    mock_http(monkeypatch, ok(rows))
    res = asyncio.run(TravelpayoutsFlights(SECRET).search("MOW", "AER"))
    assert len(res["options"]) == 5 and res["options"][0]["price_rub"] == 1000


@pytest.mark.parametrize(
    "args",
    [("Атлантида", "Москва", ""), ("Москва", "Москва", ""), ("Москва", "Сочи", "вчера"),
     ("Москва", "Сочи", "2020-01-01")],
)
def test_bad_input_returns_empty_without_calling_api(monkeypatch, args):
    def boom(request):
        raise AssertionError("API must not be called")

    mock_http(monkeypatch, boom)
    res = asyncio.run(TravelpayoutsFlights(SECRET).search(*args))
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
    assert registry.get_transport()._flights is None
    monkeypatch.setattr("app.providers.registry.settings.avia_api_key", SECRET)
    assert isinstance(registry.get_transport()._flights, TravelpayoutsFlights)


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
        registry.override("transport", Down())
        assert service.search_transport_for_agent("Москва", "Сочи")["options"] == []
    finally:
        service._loop = None
        loop.call_soon_threadsafe(loop.stop)


def plane(price, minutes, oid="p"):
    return {"id": oid, "mode": "plane", "price_rub": price, "duration_min": minutes}


def train(price, minutes, oid="t"):
    return {"id": oid, "mode": "train", "price_rub": price, "duration_min": minutes}


def test_mock_trains_estimate_from_distance():
    res = asyncio.run(MockTrains().search("Москва", "Санкт-Петербург", FUTURE))
    assert [o["car_class"] for o in res["options"]] == ["плацкарт", "купе"]
    first, second = res["options"]
    assert first["mode"] == "train" and 500 < first["duration_min"] < 900
    assert first["price_rub"] < second["price_rub"]
    assert "не расписание" in res["note"]


def test_mock_trains_respect_budget_and_unknown_cities():
    cheap = asyncio.run(MockTrains().search("MOW", "LED", max_price=2500))
    assert [o["car_class"] for o in cheap["options"]] == ["плацкарт"]
    assert asyncio.run(MockTrains().search("Москва", "Атлантида"))["options"] == []
    assert asyncio.run(MockTrains().search("Москва", "Сочи", mode="plane"))["options"] == []


def test_compare_prefers_plane_when_much_faster():
    res = compare([plane(6000, 230), train(3500, 1400)])
    assert res["recommended_mode"] == "plane" and res["reason"] == "much_faster"
    assert res["time_saved_by_plane_min"] > 240


def test_compare_prefers_train_when_close_in_time():
    res = compare([plane(5000, 90), train(1900, 540)])
    assert res["recommended_mode"] == "plane"
    res = compare([plane(9000, 90), train(1900, 250)])
    assert res["recommended_mode"] == "train" and res["reason"] == "cheaper_and_close_in_time"


def test_compare_single_mode_and_empty():
    assert compare([train(1900, 540)])["reason"] == "only_option"
    assert compare([]) is None


def test_combined_merges_modes(monkeypatch):
    mock_http(monkeypatch, ok(ROWS))
    both = asyncio.run(CombinedTransport(TravelpayoutsFlights(SECRET), MockTrains()).search("Москва", "Санкт-Петербург", FUTURE))
    assert {o["mode"] for o in both["options"]} == {"plane", "train"}
    assert both["comparison"]["recommended_mode"] in ("plane", "train")


def test_combined_survives_flight_outage(monkeypatch):
    mock_http(monkeypatch, lambda request: httpx.Response(500))
    down = asyncio.run(CombinedTransport(TravelpayoutsFlights(SECRET), MockTrains()).search("Москва", "Санкт-Петербург", FUTURE))
    assert {o["mode"] for o in down["options"]} == {"train"}
    assert "недоступны" in down["note"]


def test_combined_without_flights_key_still_gives_trains():
    res = asyncio.run(CombinedTransport(None, MockTrains()).search("Москва", "Казань"))
    assert res["options"] and "Авиабилеты не подключены" in res["note"]


def test_flights_carry_aviasales_link_and_trains_carry_car_key(monkeypatch):
    mock_http(monkeypatch, ok([{"origin": "MOW", "destination": "LED", "depart_date": "2030-01-15T09:00:00+03:00", "value": 4000}]))
    res = asyncio.run(CombinedTransport(TravelpayoutsFlights(SECRET), MockTrains()).search("Москва", "Санкт-Петербург"))
    plane_option = next(o for o in res["options"] if o["mode"] == "plane")
    assert plane_option["url"] == "https://www.aviasales.ru/search/MOW1501LED1"
    assert {o["car_key"] for o in res["options"] if o["mode"] == "train"} == {"platzkart", "coupe"}


def test_combined_shows_at_most_three_flights(monkeypatch):
    rows = [{"depart_date": FUTURE, "value": 1000 + i} for i in range(8)]
    mock_http(monkeypatch, ok(rows))
    res = asyncio.run(CombinedTransport(TravelpayoutsFlights(SECRET), MockTrains()).search("Москва", "Санкт-Петербург"))
    assert len([o for o in res["options"] if o["mode"] == "plane"]) == 3
