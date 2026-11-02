from app import nearby
from app.providers.base import ProviderUnavailable


class OverpassPlaces:
    name = "overpass"

    async def search(self, category: str, lat: float, lon: float, radius: int = 1000, **options) -> dict:
        try:
            return await nearby.search_nearby(category, lat, lon, radius, **options)
        except nearby.NearbyError as exc:
            raise ProviderUnavailable(str(exc)) from exc
