import asyncio
import threading

import pytest

from app.agent.security import clamp_limit, validate_hotel_search, validate_transport_search

pytest.importorskip("google.genai")

from app.agent import service
from app.providers import registry


def ok_hotel(**kw):
    args = dict(city="Москва", kinds=None, min_stars=None, limit=5, name_query=None)
    args.update(kw)
    validate_hotel_search(**args)


def test_hotel_validation_accepts_normal_and_rejects_garbage():
    ok_hotel()
    ok_hotel(kinds=["hostel"], min_stars=3, name_query="центр")
    for bad in (
        dict(city=""), dict(city="x" * 101), dict(kinds=["castle"]), dict(kinds="hotel"),
        dict(min_stars=7), dict(min_stars=True), dict(limit=0), dict(name_query="x" * 101),
    ):
        with pytest.raises(ValueError):
            ok_hotel(**bad)


def test_clamp_limit_never_rejects():
    assert clamp_limit(0) == 1 and clamp_limit(50) == 10 and clamp_limit(3) == 3
    assert clamp_limit(None) == 5 and clamp_limit("7") == 5 and clamp_limit(True) == 5


def test_transport_validation():
    validate_transport_search("Москва", "Сочи", "", None)
    validate_transport_search("MOW", "AER", "2030-01-15", 8000)
    for args in (("", "Сочи", "", None), ("Москва", "Сочи", "15 декабря", None), ("Москва", "Сочи", "", -5)):
        with pytest.raises(ValueError):
            validate_transport_search(*args)


class FakeHotels:
    name = "fake"
    seen = {}

    async def search(self, city, **filters):
        FakeHotels.seen = filters
        return {"city": city, "total_found": 0, "hotels": [], "note": ""}

    async def cities(self):
        return []


@pytest.fixture
def loop_in_thread():
    loop = asyncio.new_event_loop()
    threading.Thread(target=loop.run_forever, daemon=True).start()
    service._loop = loop
    yield loop
    service._loop = None
    loop.call_soon_threadsafe(loop.stop)


def test_tools_return_error_instead_of_raising(loop_in_thread):
    registry.override("hotels", FakeHotels())
    assert "error" in service.search_catalog_for_agent("Москва", kinds=["castle"])
    assert "error" in service.search_transport_for_agent("Москва", "Сочи", "завтра")


def test_oversized_limit_is_clamped_not_rejected(loop_in_thread):
    registry.override("hotels", FakeHotels())
    out = service.search_catalog_for_agent("Москва", limit=99)
    assert "error" not in out
    assert FakeHotels.seen["limit"] <= 10


def test_instruction_has_security_and_scope_rules():
    text = service.build_instruction({}, ["Москва"])
    assert "SECURITY RULES" in text and "untrusted data" in text
    assert "only help with travel" in text


def test_transport_instruction_requires_details():
    text = service.build_instruction({}, ["Москва"])
    assert "Never answer only" in text and "duration_min" in text
