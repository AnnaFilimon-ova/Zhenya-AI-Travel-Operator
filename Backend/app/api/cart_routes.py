"""API корзины для мини-аппа. Авторизация та же, что у профиля (подпись Telegram)."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.auth import current_user
from app.cart import get_cart, list_orders, remove_item, set_nights
from app.tickets import remove_ticket
from app.payments import get_provider

router = APIRouter(prefix="/api")


class NightsIn(BaseModel):
    nights: int = Field(ge=1, le=30)


@router.get("/cart")
async def read_cart(tg_user: dict = Depends(current_user)) -> dict:
    return await get_cart(tg_user["id"])


@router.patch("/cart/{item_id}")
async def change_nights(
    item_id: int, body: NightsIn, tg_user: dict = Depends(current_user)
) -> dict:
    if not await set_nights(tg_user["id"], item_id, body.nights):
        raise HTTPException(status_code=404, detail="item not found")
    return {"ok": True}


@router.delete("/cart/ticket/{ticket_id}")
async def delete_ticket(ticket_id: int, tg_user: dict = Depends(current_user)) -> dict:
    if not await remove_ticket(tg_user["id"], ticket_id):
        raise HTTPException(status_code=404, detail="item not found")
    return {"ok": True}


@router.delete("/cart/{item_id}")
async def delete_item(item_id: int, tg_user: dict = Depends(current_user)) -> dict:
    if not await remove_item(tg_user["id"], item_id):
        raise HTTPException(status_code=404, detail="item not found")
    return {"ok": True}


@router.post("/cart/checkout")
async def pay(tg_user: dict = Depends(current_user)) -> dict:
    """Начинает оплату. Режим demo: заказ сразу. Режим invoice: ссылка на счёт Telegram."""
    cart = await get_cart(tg_user["id"])
    if not cart["items"]:
        raise HTTPException(status_code=400, detail="cart is empty")
    return await get_provider().start(tg_user["id"], cart)


@router.get("/orders")
async def orders(tg_user: dict = Depends(current_user)) -> dict:
    return {"orders": await list_orders(tg_user["id"])}
