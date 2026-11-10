class OsmCatalogHotels:
    name = "osm_catalog"

    async def search(self, city: str, **filters) -> dict:
        from app.hotels_world import search_near

        return await search_near(city=city, **filters)

    async def cities(self) -> list[dict]:
        from app.catalog import list_cities

        return await list_cities()
