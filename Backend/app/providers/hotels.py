class OsmCatalogHotels:
    name = "osm_catalog"

    async def search(self, city: str, **filters) -> dict:
        from app.catalog import search_catalog

        return await search_catalog(city=city, **filters)

    async def cities(self) -> list[dict]:
        from app.catalog import list_cities

        return await list_cities()
