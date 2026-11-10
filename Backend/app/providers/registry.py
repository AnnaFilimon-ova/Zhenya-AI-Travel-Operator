from app.providers.base import (
    HotelProvider,
    PaymentProvider,
    PlacesProvider,
    TransportProvider,
    WeatherProvider,
)
from app.providers.hotels import OsmCatalogHotels
from app.providers.places import OverpassPlaces
from app.config import settings
from app.providers.transport import NoTransport, TravelpayoutsFlights
from app.providers.weather import OpenMeteoWeather

_overrides: dict[str, object] = {}


def override(kind: str, provider: object) -> None:
    _overrides[kind] = provider


def reset() -> None:
    _overrides.clear()


def get_hotels() -> HotelProvider:
    return _overrides.get("hotels") or OsmCatalogHotels()


def get_places() -> PlacesProvider:
    return _overrides.get("places") or OverpassPlaces()


def get_transport() -> TransportProvider:
    if "transport" in _overrides:
        return _overrides["transport"]
    if settings.avia_api_key:
        return TravelpayoutsFlights(settings.avia_api_key)
    return NoTransport()


def get_weather() -> WeatherProvider:
    return _overrides.get("weather") or OpenMeteoWeather()


def get_payments() -> PaymentProvider:
    if "payments" in _overrides:
        return _overrides["payments"]
    from app.payments import get_provider

    return get_provider()
