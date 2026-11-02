from datetime import date

ALLOWED_KINDS = {
    "hotel",
    "hostel",
    "guest_house",
    "apartment",
    "motel",
    "chalet",
}

def validate_hotel_search(
    city: str,
    kinds: list[str] | None,
    min_stars: int | None,
    limit: int,
    name_query: str | None,
) -> None:
    if not isinstance(city, str) or not city.strip():
        raise ValueError("Invalid city")

    if len(city) > 100:
        raise ValueError("City name is too long")

    if kinds is not None:
        if not isinstance(kinds, list):
            raise ValueError("Invalid kinds")

        if len(kinds) > len(ALLOWED_KINDS):
            raise ValueError("Invalid kinds")

        if any(
            not isinstance(kind, str)
            or kind not in ALLOWED_KINDS
            for kind in kinds
        ):
            raise ValueError("Invalid kinds")

    if min_stars is not None:
        if (
            isinstance(min_stars, bool)
            or not isinstance(min_stars, int)
            or not 1 <= min_stars <= 5
        ):
            raise ValueError("Invalid min_stars")

    if (
        isinstance(limit, bool)
        or not isinstance(limit, int)
        or not 1 <= limit <= 10
    ):
        raise ValueError("Invalid limit")

    if name_query is not None:
        if not isinstance(name_query, str):
            raise ValueError("Invalid name_query")

        if len(name_query) > 100:
            raise ValueError("Name query is too long")


def clamp_limit(limit: object, default: int = 5, maximum: int = 10) -> int:
    if isinstance(limit, bool) or not isinstance(limit, int):
        return default
    return max(1, min(limit, maximum))


def validate_transport_search(
    origin: str,
    destination: str,
    day: str,
    max_price: int | None,
    mode: str = "any",
) -> None:
    if mode not in ("any", "plane", "train"):
        raise ValueError("mode must be any, plane or train")

    for place in (origin, destination):
        if not isinstance(place, str) or not place.strip() or len(place) > 100:
            raise ValueError("Invalid city")

    if day:
        if not isinstance(day, str):
            raise ValueError("Invalid date")
        try:
            date.fromisoformat(day)
        except ValueError:
            raise ValueError("Date must be YYYY-MM-DD") from None

    if max_price is not None:
        if isinstance(max_price, bool) or not isinstance(max_price, (int, float)) or max_price < 0:
            raise ValueError("Invalid max_price")
