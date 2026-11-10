import asyncio

from app import geocode


class _Resp:
    def __init__(self, data):
        self._data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self._data


def _client(data, calls):
    class Client:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, url, params=None):
            calls.append(params["q"])
            return _Resp(data)

    return Client


PARIS = [
    {"lat": "48.85", "lon": "2.35", "name": "Paris", "address": {"country": "France", "state": "Île-de-France"}},
    {"lat": "bad", "lon": "1", "name": "Broken"},
]


def _reset(monkeypatch, data, calls):
    monkeypatch.setattr(geocode.httpx, "AsyncClient", _client(data, calls))
    monkeypatch.setattr(geocode, "MIN_GAP", 0)
    geocode._cache.clear()


def test_search_parses_and_caches(monkeypatch):
    calls = []
    _reset(monkeypatch, PARIS, calls)
    first = asyncio.run(geocode.search_places("Paris", lang="en"))
    asyncio.run(geocode.search_places("paris", lang="en"))
    assert first == [{"name": "Paris", "label": "Paris, Île-de-France, France", "lat": 48.85, "lon": 2.35, "country": "France"}]
    assert len(calls) == 1


def test_short_query_is_empty(monkeypatch):
    calls = []
    _reset(monkeypatch, PARIS, calls)
    assert asyncio.run(geocode.search_places("a")) == []
    assert calls == []


def test_catalog_city_goes_first(monkeypatch):
    calls = []
    _reset(monkeypatch, [], calls)
    found = asyncio.run(geocode.search_places("Каз"))
    assert found[0]["name"] == "Казань"


def test_resolve_center(monkeypatch):
    calls = []
    _reset(monkeypatch, PARIS, calls)
    assert asyncio.run(geocode.resolve_center("Сочи"))[2] == "Сочи"
    lat, lon, label = asyncio.run(geocode.resolve_center("Paris"))
    assert (lat, lon) == (48.85, 2.35) and "France" in label
