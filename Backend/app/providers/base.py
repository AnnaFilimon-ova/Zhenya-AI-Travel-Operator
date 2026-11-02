from datetime import date
from typing import Protocol


class ProviderError(Exception):
    pass


class ProviderUnavailable(ProviderError):
    pass


class HotelProvider(Protocol):


    name: str

    async def search(
        self,
        city: str,
        *,
        kinds: list[str] | None = None,
        min_stars: int | None = None,
        want_pets: bool = False,
        want_accessible: bool = False,
        only_confirmed: bool = False,
        name_query: str | None = None,
        max_price: int | None = None,
        limit: int = 10,
    ) -> dict:

        ...

    async def cities(self) -> list[dict]:

        ...


class PlacesProvider(Protocol):
    name: str

    async def search(
        self,
        category: str,
        lat: float,
        lon: float,
        radius: int = 1000,
        *,
        limit: int = 40,
        food_prefs: list[str] | None = None,
        accessible: bool = False,
        with_pets: bool = False,
    ) -> dict:
        ...


class TransportProvider(Protocol):

    name: str

    async def search(
        self,
        origin: str,
        destination: str,
        date: str,
        *,
        mode: str = "any",
        adults: int = 1,
        max_price: int | None = None,
    ) -> dict:

        ...


class WeatherProvider(Protocol):

    name: str

    async def summary(self, lat: float, lon: float, start: date, end: date) -> dict:

        ...


class PaymentProvider(Protocol):


    name: str

    async def start(self, telegram_id: int, cart: dict) -> dict:
        ...
