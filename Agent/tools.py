import os
from dotenv import load_dotenv
import requests

load_dotenv()

avias_api_key = os.getenv("AVIAS_API_KEY")

url = "https://api.stayingapi.com/v1/search"

print(
    "StayingAPI key type:",
    "LIVE" if (hotels_api_key or "").startswith("stay_live_")
    else "TEST" if (hotels_api_key or "").startswith("stay_test_")
    else "UNKNOWN"
)

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
        "currency": currency,
    }

    headers = {
        "Authorization": f"Bearer {hotels_api_key}",
    }

    response = requests.get(
        url,
        headers=headers,
        params=params,
        timeout=30,
    )

    print("API STATUS:", response.status_code)

    response.raise_for_status()
    data = response.json()

    # Live-поиск может вернуть задачу вместо списка отелей
    if response.status_code == 202:
        job_id = data.get("data", {}).get("jobId")

        if not job_id:
            raise RuntimeError(
                f"API вернул 202 без jobId: {data}"
            )

        job_url = f"https://api.stayingapi.com/v1/jobs/{job_id}"

        import time

        deadline = time.monotonic() + 300

        while time.monotonic() < deadline:
            time.sleep(5)

            job_response = requests.get(
                job_url,
                headers=headers,
                timeout=30,
            )
            job_response.raise_for_status()
            job_data = job_response.json()
            job = job_data.get("data", {})

            status = job.get("status")
            print("Search job status:", status)

            if status == "completed":
                result = job.get("result")

                if not isinstance(result, list):
                    raise RuntimeError(
                        f"Неожиданный формат результата: {type(result).__name__}"
                    )

                data = {
                    "data": result,
                    "meta": job_data.get("meta", {}),
                }
                break

                if not isinstance(data, dict):
                    raise RuntimeError(
                        f"Нет результатов в завершённой задаче: {job_data}"
                    )

                break

            if status in {"failed", "cancelled", "canceled", "expired"}:
                raise RuntimeError(
                    f"Поиск отелей завершился со статусом {status}: {job_data}"
                )
        else:
            raise TimeoutError(
                "StayingAPI не завершил поиск за 5 минут."
            )

    print("FINAL SEARCH RESULT:", data)
    #временно
    print("SANDBOX VALUE:", data.get("meta", {}).get("sandbox"))
    print("RESULT KEYS:", list(data.keys()))
    print("HOTELS COUNT:", len(data.get("data", [])))

    # Не используем тестовые отели как реальные результаты
    if data.get("meta", {}).get("sandbox") is True:
        print("WARNING: StayingAPI returned sandbox data.")
        print("These hotels are test examples, not real search results.")

        data["data"] = []
        data["unknown_details"] = []

        return data

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

def filter_hotels(
    hotels: list[dict],
    min_price: float | None = None,
    max_price: float | None = None,
    min_rating: float | None = None,
    required_amenities: list[str] | None = None,
    pets_allowed: bool | None = None,
) -> list[dict]:
    print("DEBUG: filter_hotels was called")

    filtered_hotels = []

    for hotel in hotels:
        price = hotel.get("nightly_price")
        rating = hotel.get("rating")
        amenities = hotel.get("amenities") or []

        if min_price is not None:
            if price is None or price < min_price:
                continue

        if max_price is not None:
            if price is None or price > max_price:
                continue

        if min_rating is not None:
            if rating is None or rating < min_rating:
                continue

        if required_amenities:
            normalized_amenities = {
                item.lower() for item in amenities
            }

            if not all (
                item.lower() in normalized_amenities
                for item in required_amenities
            ):
                continue

        if pets_allowed is True:
            if hotel.get("pet_policy") is not True:
                continue

        if pets_allowed is False:
            if hotel.get("pet_policy") is not False:
                continue

        filtered_hotels.append(hotel)

    return filtered_hotels

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

def format_hotel_results(data):
    hotels = []

    for hotel in data.get("data", []):
        price = hotel.get("price") or {}
        location = hotel.get("location") or {}

        hotels.append({
            "name": hotel.get("name"),
            "location": location.get("address")
                        or location.get("city"),
            "url": hotel.get("url"),
            "nightly_price": price.get("nightlyPrice"),
            "currency": price.get("currency"),
            "total_price": price.get("totalPrice"),
            "nights": price.get("nights"),
            "max_occupancy": hotel.get("maxOccupancy"),
            "rating": hotel.get("guestRating"),
            "review_count": hotel.get("reviewCount"),
            "amenities": hotel.get("amenities", []),
            "pet_policy": hotel.get("pet_policy", "unknown"),
            "accessibility": hotel.get(
                "accessibility_status", {}
            ),
        })

    return {
        "hotels": hotels,
        "sandbox": data.get("meta", {}).get("sandbox", False),
        "warnings": data.get("meta", {}).get("warnings", []),
        "unknown_details": data.get("unknown_details", []),
    }

