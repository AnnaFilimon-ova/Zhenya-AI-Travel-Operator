import os
from locale import normalize

from dotenv import load_dotenv
import hashlib
import time
import requests
from pip._internal.resolution.resolvelib import requirements

load_dotenv()

hotels_api_key = os.getenv("HOTELS_API_KEY")

url = "https://api.stayingapi.com/v1/search"

def get_amenity_status(amenities, keywords):
    normalized = {
        str(item).lower().replace("_", " ")
        for item in amenities
    }

    if any(
        keyword.lower() in amenity
        for amenity in normalized
        for keyword in keywords
    ):
        return True

    return None

def search_hotels(
    location: str,
    check_in: str,
    check_out: str,
    adults: int = 2,
    children: int = 0,
    children_ages: list[int] | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    currency: str = "EUR",
    pets_allowed: bool = False,
    accessibility: list[str] | None = None,
    limit: int = 5,
):
    print("\n--- HOTEL SEARCH PARAMETERS ---")
    print("Location:", location)
    print("Check-in:", check_in)
    print("Check-out:", check_out)
    print("Adults:", adults)
    print("Children:", children)
    print("Children's ages:", children_ages)
    print("Minimum price:", min_price)
    print("Maximum price:", max_price)
    print("Pets allowed:", pets_allowed)
    print("Accessibility:", accessibility)
    print("-------------------------------\n")

    if not hotels_api_key:
        raise ValueError("Hotels API key not set")

    if not location.strip():
        raise ValueError("Location not set")

    if adults < 1 or children < 0:
        raise ValueError("Invalid number of adults or children")

    if limit < 1:
        raise ValueError("Limit must be at least 1")

    if min_price is not None and min_price < 0:
        raise ValueError("Minimum price cannot be negative")

    if max_price is not None and max_price < 0:
        raise ValueError("Maximum price cannot be negative")

    if (
        min_price is not None
        and max_price is not None
        and min_price > max_price
    ):
        raise ValueError("Minimum price cannot be greater than maximum price")

    children_ages = children_ages or []
    accessibility = accessibility or []

    if len(children_ages) != children:
        raise ValueError("Provide an age for each child")

    params = {
        "location": location,
        "check_in": check_in,
        "check_out": check_out,
        "platforms": "booking",
        "limit": limit,
    }

    headers = {
        "Authorization": f"Bearer {hotels_api_key}",
    }

    response = requests.get(url, headers=headers, params=params, timeout=30,)
    response.raise_for_status()
    data = response.json()

    results = data.get("data", [])

    unknown_details = []

    for hotel in results:
        amenities = hotel.get("amenities", [])

        hotel["pet_policy"] = get_amenity_status(
            amenities,
            ["pets allowed", "pet friendly", "pets permitted"],
        )

        hotel["accessibility_status"] = {
            "wheelchair": get_amenity_status(
                amenities,
                ["wheelchair accessible", "wheelchair access"],
            )
        }

        if hotel["pet_policy"] is None:
            unknown_details.append({
                "hotel": hotel.get("name"),
                "detail": "pet policy",
            })

        if hotel["accessibility_status"]["wheelchair"] is None:
            unknown_details.append({
                "hotel": hotel.get("name"),
                "detail": "wheelchair accessible",
            })

    data["unknown_details"] = unknown_details

    if min_price is not None:
        results = [
            hotel for hotel in results
            if hotel.get("price", {}).get("nightlyPrice") is not None
            and hotel["price"]["nightlyPrice"] >= min_price
        ]

    if max_price is not None:
        results = [
            hotel for hotel in results
            if hotel.get("price", {}).get("nightlyPrice") is not None
            and hotel["price"]["nightlyPrice"] <= max_price
        ]

    print("Hotels returned by API:", len(data.get("data", [])))
    print("Hotels after filtering:", len(results))

    for hotel in data.get("data", []):
        print("\nHotel:", hotel.get("name"))
        print("Price:", hotel.get("price"))
        print("Amenities:", hotel.get("amenities"))

    data["data"] = results
    return data

if __name__ == "__main__":
    result = search_hotels(
        location="New York",
        check_in="2026-11-10",
        check_out="2026-11-15",
        adults=2,
        children=1,
        children_ages=[0],
        min_price=50,
        max_price=550,
        pets_allowed=True,
        accessibility=["wheelchair"],
        limit=5,
    )

    print(result)