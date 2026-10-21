from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from app.api.auth import current_user
from app.db import SessionLocal
from app.models import User, UserPreferences

WEBAPP_DIR = Path(__file__).resolve().parents[2] / "webapp"

TRAVEL_TYPES = {"beach", "city", "nature", "culture", "active", "relax", "gastro", "nightlife"}
FOOD_PREFS = {
    "vegetarian", "vegan", "halal", "kosher", "gluten_free",
    "lactose_free", "no_alcohol", "nut_allergy", "spicy", "seafood",
}

app = FastAPI(title="Zhenya API")


class ProfileIn(BaseModel):
    display_name: str = Field(default="", max_length=50)
    gender: Literal["", "female", "male", "other"] = ""
    with_pets: bool = False
    accessible: bool = False
    travel_types: list[str] = Field(default_factory=list, max_length=10)
    food_prefs: list[str] = Field(default_factory=list, max_length=12)
    favorite_places: str = Field(default="", max_length=500)


async def get_or_create_user(session, tg_user: dict) -> User:
    stmt = insert(User).values(
        telegram_id=tg_user["id"],
        username=tg_user.get("username"),
        first_name=tg_user.get("first_name"),
    )
    stmt = stmt.on_conflict_do_nothing(index_elements=[User.telegram_id])
    await session.execute(stmt)
    result = await session.execute(
        select(User).where(User.telegram_id == tg_user["id"])
    )
    return result.scalar_one()


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/api/me")
async def me(tg_user: dict = Depends(current_user)) -> dict:
    return {"id": tg_user["id"], "first_name": tg_user.get("first_name")}


@app.get("/api/profile")
async def get_profile(tg_user: dict = Depends(current_user)) -> dict:
    async with SessionLocal() as session:
        user = await get_or_create_user(session, tg_user)
        prefs = await session.get(UserPreferences, user.id)
        await session.commit()
        return {
            "display_name": user.display_name or user.first_name or "",
            "gender": user.gender or "",
            "with_pets": prefs.with_pets if prefs else False,
            "accessible": prefs.accessible if prefs else False,
            "travel_types": list(prefs.travel_types or []) if prefs else [],
            "food_prefs": list(prefs.food_prefs or []) if prefs else [],
            "favorite_places": (prefs.favorite_places or "") if prefs else "",
        }


@app.put("/api/profile")
async def save_profile(
    body: ProfileIn, tg_user: dict = Depends(current_user)
) -> dict:
    travel_types = sorted({t for t in body.travel_types if t in TRAVEL_TYPES})
    food_prefs = sorted({f for f in body.food_prefs if f in FOOD_PREFS})
    favorite_places = body.favorite_places.strip()

    async with SessionLocal() as session:
        user = await get_or_create_user(session, tg_user)
        user.display_name = body.display_name.strip() or None
        user.gender = body.gender or None

        stmt = insert(UserPreferences).values(
            user_id=user.id,
            with_pets=body.with_pets,
            accessible=body.accessible,
            travel_types=travel_types,
            food_prefs=food_prefs,
            favorite_places=favorite_places or None,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[UserPreferences.user_id],
            set_={
                "with_pets": stmt.excluded.with_pets,
                "accessible": stmt.excluded.accessible,
                "travel_types": stmt.excluded.travel_types,
                "food_prefs": stmt.excluded.food_prefs,
                "favorite_places": stmt.excluded.favorite_places,
                "updated_at": func.now(),
            },
        )
        await session.execute(stmt)
        await session.commit()
    return {"ok": True}


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(WEBAPP_DIR / "index.html")


app.mount("/static", StaticFiles(directory=WEBAPP_DIR), name="static")