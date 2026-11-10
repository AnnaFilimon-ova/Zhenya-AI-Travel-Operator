CITY_CENTERS = {
    "Москва": (55.7558, 37.6173),
    "Санкт-Петербург": (59.9343, 30.3351),
    "Сочи": (43.5855, 39.7231),
    "Казань": (55.7887, 49.1221),
    "Калининград": (54.7104, 20.4522),
    "Екатеринбург": (56.8389, 60.6057),
    "Нижний Новгород": (56.2965, 43.9361),
    "Иркутск": (52.2870, 104.3050),
    "Кисловодск": (43.9052, 42.7168),
    "Рязань": (54.6269, 39.6916),
}


CITY_IATA = {
    "Москва": "MOW",
    "Санкт-Петербург": "LED",
    "Сочи": "AER",
    "Казань": "KZN",
    "Калининград": "KGD",
    "Екатеринбург": "SVX",
    "Нижний Новгород": "GOJ",
    "Иркутск": "IKT",
    "Кисловодск": "MRV",
}


def resolve_iata(place: str) -> str | None:
    place = (place or "").strip()
    if place in CITY_IATA:
        return CITY_IATA[place]
    if len(place) == 3 and place.isascii() and place.isalpha():
        return place.upper()
    return None


def resolve_city(place: str) -> str | None:
    place = (place or "").strip()
    if place in CITY_CENTERS:
        return place
    code = place.upper()
    for city, iata in CITY_IATA.items():
        if iata == code:
            return city
    return None
