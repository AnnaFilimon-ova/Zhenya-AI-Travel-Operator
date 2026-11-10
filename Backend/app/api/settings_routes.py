from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.auth import current_user
from app.settings_store import get_persona, set_persona

router = APIRouter(prefix="/api")


class SettingsIn(BaseModel):
    persona: Literal["female", "male", "any"]


@router.get("/settings")
async def read_settings(tg_user: dict = Depends(current_user)) -> dict:
    return {"persona": await get_persona(tg_user["id"])}


@router.put("/settings")
async def save_settings(body: SettingsIn, tg_user: dict = Depends(current_user)) -> dict:
    return {"persona": await set_persona(tg_user, body.persona)}
