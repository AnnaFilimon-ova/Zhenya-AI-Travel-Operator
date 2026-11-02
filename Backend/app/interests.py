from app.nearby import CATEGORIES

TRAVEL_TO_PLACES = {
    "beach": ["beach"],
    "city": ["sights"],
    "nature": ["nature"],
    "culture": ["culture"],
    "active": ["active"],
    "relax": ["relax", "nature"],
    "gastro": ["food"],
    "nightlife": ["evening"],
    "gothic": ["gothic"],
    "aesthetic": ["sights", "nature"],
    "music": ["music"],
    "shopping": ["shopping"],
}


def suggested_categories(travel_types: list[str]) -> list[str]:
    out: list[str] = []
    for kind in travel_types:
        for category in TRAVEL_TO_PLACES.get(kind, []):
            if category in CATEGORIES and category not in out:
                out.append(category)
    return out
