import asyncio
import json

import pytest

from app import nearby as n


def run(coro):
    return asyncio.run(coro)


def test_query_uses_exact_tag_values():
    q = n.build_query("food", 55.79, 49.12, 1000)
    assert '["amenity"="restaurant"]' in q
    assert "around:1000,55.79000,49.12000" in q
    assert q.rstrip().endswith("out center tags 500;")


def test_parse_skips_abandoned_nameless_and_duplicates():
    els = [
        {"type": "node", "id": 1, "lat": 55.791, "lon": 49.121,
         "tags": {"name": "Веган Кафе", "amenity": "cafe", "cuisine": "vegan;coffee_shop",
                  "diet:vegan": "yes", "wheelchair": "yes",
                  "addr:street": "Баумана", "addr:housenumber": "5"}},
        {"type": "way", "id": 2, "center": {"lat": 55.7915, "lon": 49.1215},
         "tags": {"name": "Старый дом", "historic": "ruins"}},
        {"type": "node", "id": 3, "lat": 55.8, "lon": 49.13, "tags": {"name": "Парк", "leisure": "park"}},
        {"type": "node", "id": 4, "lat": 55.8, "lon": 49.13, "tags": {"name": "парк", "leisure": "park"}},
        {"type": "node", "id": 5, "lat": 55.8, "lon": 49.1, "tags": {"amenity": "cafe"}},
        {"type": "node", "id": 6, "lat": 55.792, "lon": 49.1215,
         "tags": {"name": "Заброшка", "amenity": "cafe", "abandoned:amenity": "cafe"}},
    ]
    items = n.parse_elements(els, 55.79, 49.12, ["vegan"], True, False)
    assert [i["name"] for i in items] == ["Веган Кафе", "Парк"]  # по возрастанию расстояния
    first = items[0]
    assert first["address"] == "Баумана, 5"
    assert first["cuisine"] == "веганская, кофе"
    # отметки из профиля подсвечиваются (match), если совпадают
    assert {b["text"]: b["match"] for b in first["badges"]} == {
        "есть веганское": True, "доступно на коляске": True,
    }


def test_distance_is_sane():
    assert n.distance_m(55.0, 37.0, 55.0, 37.0) == 0
    assert 110_000 < n.distance_m(55.0, 37.0, 56.0, 37.0) < 112_000  # ~111 км на градус


def test_fetch_takes_first_successful_mirror(monkeypatch):
    async def fake_ask(client, url, query):
        if "overpass-api.de" in url:
            raise n.httpx.HTTPError("down")
        if "kumi" in url:
            await asyncio.sleep(0.3)
            return [{"id": "slow"}]
        await asyncio.sleep(0.02)
        return [{"id": "fast"}]

    monkeypatch.setattr(n, "_ask", fake_ask)
    assert run(n.fetch_overpass("q")) == [{"id": "fast"}]


def test_all_mirrors_down_raises(monkeypatch):
    async def dead(client, url, query):
        raise n.httpx.HTTPError("down")

    monkeypatch.setattr(n, "_ask", dead)
    with pytest.raises(n.NearbyError):
        run(n.fetch_overpass("q"))


@pytest.fixture
def seed_file(tmp_path, monkeypatch):
    path = tmp_path / "seed.json"
    path.write_text(json.dumps({"Казань": {"food": [
        {"type": "node", "id": 1, "lat": 55.7887, "lon": 49.1225, "tags": {"name": "Рядом", "amenity": "cafe"}},
        {"type": "node", "id": 2, "lat": 55.80, "lon": 49.30, "tags": {"name": "Далеко", "amenity": "cafe"}},
    ]}}, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(n, "SEED_PATH", path)
    monkeypatch.setattr(n, "_seed", None)
    n._cache.clear()

    async def dead(*args, **kwargs):
        raise n.NearbyError("down")

    monkeypatch.setattr(n, "fetch_overpass", dead)


def test_falls_back_to_saved_copy_and_respects_radius(seed_file):
    result = run(n.search_nearby("food", 55.7887, 49.1221, 1000))
    assert result["offline"] is True
    assert [i["name"] for i in result["items"]] == ["Рядом"]


def test_no_copy_for_far_place_or_missing_category(seed_file):
    with pytest.raises(n.NearbyError):
        run(n.search_nearby("food", 56.0, 60.0, 1000))  # не рядом ни с одним городом из копии
    with pytest.raises(n.NearbyError):
        run(n.search_nearby("sights", 55.7887, 49.1221, 1000))  # такой категории в копии нет


def test_items_carry_codes_for_localization():
    from app.nearby import CUISINES, KIND_LABELS, parse_elements

    els = [
        {"type": "node", "id": 1, "lat": 55.75, "lon": 37.62,
         "tags": {"name": "Тратория", "amenity": "restaurant", "cuisine": "italian;pizza;thai",
                  "diet:vegan": "yes", "wheelchair": "yes", "dog": "yes"}},
        {"type": "node", "id": 2, "lat": 55.751, "lon": 37.621,
         "tags": {"name": "Собор", "building": "cathedral"}},
        {"type": "node", "id": 3, "lat": 55.752, "lon": 37.622,
         "tags": {"name": "Дом", "building:architecture": "gothic_revival"}},
        {"type": "node", "id": 4, "lat": 55.753, "lon": 37.623, "tags": {"name": "Что-то"}},
    ]
    items = parse_elements(els, 55.75, 37.62, ["vegan"], True, False)
    by_name = {i["name"]: i for i in items}
    cafe = by_name["Тратория"]
    assert cafe["kind_key"] == "restaurant" and cafe["kind"] == KIND_LABELS["restaurant"]
    assert cafe["cuisine_keys"] == ["italian", "pizza"] and cafe["cuisine"] == "итальянская, пицца"
    assert {b["key"] for b in cafe["badges"]} == {"vegan", "wheelchair", "dog"}
    assert all(b["text"] for b in cafe["badges"])
    assert by_name["Собор"]["kind_key"] == "cathedral"
    assert by_name["Дом"]["kind_key"] == "gothic_building" and by_name["Дом"]["kind"] == "здание в готическом стиле"
    assert by_name["Что-то"]["kind_key"] == "place" and by_name["Что-то"]["kind"] == "место"
    assert set(cafe["cuisine_keys"]) <= set(CUISINES)
