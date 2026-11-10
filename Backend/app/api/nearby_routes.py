"""API «Места рядом» для мини-аппа."""
from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.auth import current_user
from app.geocode import GeocodeError, search_places
from app.interests import suggested_categories
from app.nearby import ALLOWED_RADIUS, CATEGORIES, CITY_CENTERS
from app.profile import get_profile
from app.providers.base import ProviderUnavailable
from app.providers.registry import get_places

router = APIRouter(prefix="/api")

NOTE = (
    "Данные © участники OpenStreetMap. Рейтингов и отзывов в этом источнике нет, "
    "отметки про диету и доступность есть только у части мест."
)


@router.get("/nearby/categories")
async def categories(tg_user: dict = Depends(current_user)) -> dict:
    """Категории мест. Подходящие интересам из профиля помечены и стоят первыми."""
    profile = await get_profile(tg_user["id"])
    suggested = suggested_categories(profile.get("travel_types", []))
    keys = suggested + [k for k in CATEGORIES if k not in suggested]
    return {
        "categories": [
            {"key": k, "label": CATEGORIES[k]["label"], "suggested": k in suggested} for k in keys
        ]
    }


@router.get("/nearby/cities")
async def cities() -> dict:
    return {"cities": list(CITY_CENTERS)}


@router.get("/geocode")
async def geocode(
    q: str = Query(min_length=2, max_length=80),
    lang: str = "ru",
    tg_user: dict = Depends(current_user),
) -> dict:
    try:
        results = await search_places(q, lang)
    except GeocodeError:
        raise HTTPException(status_code=503, detail="geocoder unavailable")
    return {"results": results}


@router.get("/nearby")
async def nearby(
    category: str = "food",
    radius: int = 1000,
    lat: float | None = Query(default=None, ge=-90, le=90),
    lon: float | None = Query(default=None, ge=-180, le=180),
    city: str | None = None,
    tg_user: dict = Depends(current_user),
) -> dict:
    if category not in CATEGORIES:
        raise HTTPException(status_code=400, detail="unknown category")
    if radius not in ALLOWED_RADIUS:
        radius = 1000
    if city:
        if city not in CITY_CENTERS:
            raise HTTPException(status_code=400, detail="unknown city")
        lat, lon = CITY_CENTERS[city]
    if lat is None or lon is None:
        raise HTTPException(status_code=400, detail="need lat/lon or city")
    profile = await get_profile(tg_user["id"])
    try:
        result = await get_places().search(
            category, lat, lon, radius,
            food_prefs=profile.get("food_prefs", []),
            accessible=profile.get("accessible", False),
            with_pets=profile.get("with_pets", False),
        )
    except ProviderUnavailable:
        raise HTTPException(status_code=503, detail="source unavailable")
    note = NOTE + (
        " Сейчас сервер карт недоступен, показана сохранённая копия данных: она может быть неполной."
        if result.get("offline")
        else ""
    )
    return {**result, "center": {"lat": lat, "lon": lon, "city": city}, "note": note}
