from types import SimpleNamespace

from app.catalog import estimate_price


def hotel(**kw):
    base = dict(kind="hotel", stars=3, city="Казань", osm_id=123456)
    base.update(kw)
    return SimpleNamespace(**base)


def test_price_is_stable_for_one_hotel():
    assert estimate_price(hotel()) == estimate_price(hotel())


def test_hostel_cheaper_than_five_stars_and_city_matters():
    assert estimate_price(hotel(kind="hostel", stars=None)) < estimate_price(hotel(stars=5))
    assert estimate_price(hotel(city="Москва")) > estimate_price(hotel(city="Рязань"))


def test_price_within_jitter_bounds():
    for osm_id in range(1, 200):
        p = estimate_price(hotel(osm_id=osm_id))
        assert 4000 <= p <= 5500
