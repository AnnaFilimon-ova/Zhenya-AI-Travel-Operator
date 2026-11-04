import os
from typing import Any
import requests
from dotenv import load_dotenv

load_dotenv()

AVIA_API_KEY = os.getenv("AVIA_API_KEY")

API_URL = (
    "https://api.travelpayouts.com/"
    "aviasales/v3/get_latest_prices"
)


def filter_planes(
    planes: list[dict[str, Any]],
    min_price: float | None = None,
    max_price: float | None = None,
) -> list[dict[str, Any]]:
    """Filter flight offers by price."""
    results = []

    for plane in planes:
        price = plane.get("value")

        if not isinstance(price, (int, float)):
            continue

        if min_price is not None and price < min_price:
            continue

        if max_price is not None and price > max_price:
            continue

        results.append(plane)

    return results


def format_plane_results(
    planes: list[dict[str, Any]],
    currency: str = "RUB",
) -> dict[str, list[dict[str, Any]]]:
    """Convert API results into a consistent format."""
    formatted_planes = []

    for plane in planes:
        formatted_planes.append({
            "origin": plane.get("origin"),
            "destination": plane.get("destination"),
            "departure_date": plane.get("depart_date"),
            "return_date": plane.get("return_date"),
            "price": plane.get("value"),
            "currency": currency.upper(),
            "transfers": plane.get("number_of_changes"),
            "found_at": plane.get("found_at"),
            "actual": plane.get("actual"),
            "trip_class": plane.get("trip_class"),
        })

    return {"planes": formatted_planes}


def search_planes(
    origin: str,
    destination: str,
    currency: str = "RUB",
    min_price: float | None = None,
    max_price: float | None = None,
    period_type: str | None = None,
    beginning_of_period: str | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Search cached flight prices using Travelpayouts."""

    if not AVIA_API_KEY:
        raise ValueError("No AVIA_API_KEY found in .env")

    if not origin or not origin.strip():
        raise ValueError("Origin is required")

    if not destination or not destination.strip():
        raise ValueError("Destination is required")

    if min_price is not None and min_price < 0:
        raise ValueError("Minimum price cannot be negative")

    if max_price is not None and max_price < 0:
        raise ValueError("Maximum price cannot be negative")

    if (
        min_price is not None
        and max_price is not None
        and min_price > max_price
    ):
        raise ValueError(
            "Minimum price cannot be greater than maximum price"
        )

    if period_type not in (None, "day", "month", "year"):
        raise ValueError("period_type must be day, month, year, or None")

    if period_type == "month" and not beginning_of_period:
        raise ValueError(
            "beginning_of_period is required for monthly searches"
        )

    params = {
        "origin": origin.strip().upper(),
        "destination": destination.strip().upper(),
        "currency": currency.lower(),
        "token": AVIA_API_KEY,
        "market": "ru",
        "sorting": "price",
        "page": 1,
        "one_way": "true",
    }

    if period_type:
        params["period_type"] = period_type

    if beginning_of_period:
        params["beginning_of_period"] = beginning_of_period

    response = requests.get(
        API_URL,
        params=params,
        timeout=30,
    )
    response.raise_for_status()

    data = response.json()

    if not data.get("success", False):
        raise RuntimeError(
            f"Travelpayouts API error: {data.get('error')}"
        )

    raw_planes = data.get("data", [])

    if not isinstance(raw_planes, list):
        raise ValueError("Unexpected API response: data is not a list")

    filtered_planes = filter_planes(
        raw_planes,
        min_price=min_price,
        max_price=max_price,
    )

    result = format_plane_results(
        filtered_planes,
        currency=currency,
    )

    print("Flights returned by API:", len(raw_planes))
    print("Flights after filtering:", len(filtered_planes))

    return result


if __name__ == "__main__":
    try:
        result = search_planes(
            origin="MOW",
            destination="LED",
            currency="RUB",
            min_price=1000,
            max_price=10000,
        )

        for plane in result["planes"]:
            print("\n-----------------------------")
            print("Route:", plane["origin"], "->", plane["destination"])
            print("Departure:", plane["departure_date"])
            print("Return:", plane["return_date"])
            print("Price:", plane["price"], plane["currency"])
            print("Transfers:", plane["transfers"])
            print("Price is current:", plane["actual"])

        if not result["planes"]:
            print("No flights found matching these filters.")

    except (requests.RequestException, ValueError, RuntimeError) as error:
        print(f"Flight search failed: {error}")
