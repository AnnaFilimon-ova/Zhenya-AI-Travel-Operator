from tools import filter_hotels

hotels = [
    {
        "name": "Hotel A",
        "nightly_price": 120,
        "rating": 9.2,
        "amenities": ["wifi", "parking_free"],
        "pet_policy": True,
    },
    {
        "name": "Hotel B",
        "nightly_price": 180,
        "rating": 8.7,
        "amenities": ["wifi"],
        "pet_policy": False,
    },
    {
        "name": "Hotel C",
        "nightly_price": 90,
        "rating": 7.9,
        "amenities": ["wifi"],
        "pet_policy": None,
    },
]

results = filter_hotels(
    hotels,
    max_price=150,
    min_rating=8.0,
    required_amenities=["wifi"],
    pets_allowed=True,
)

print([hotel["name"] for hotel in results])