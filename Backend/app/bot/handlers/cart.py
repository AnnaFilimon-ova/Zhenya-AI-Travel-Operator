from aiogram import F, Router
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    PreCheckoutQuery,
    WebAppInfo,
)

from app.agent.service import find_ticket
from app.cart import add_to_cart, checkout, get_cart
from app.tickets import add_ticket
from app.config import settings
from app.payments import PROVIDER_TELEGRAM

router = Router()


def ticket_title(ticket: dict) -> str:
    title = f"✈️ {ticket['origin']} → {ticket['destination']} · {ticket['price_rub']} ₽"
    return title[:60]


def offered_keyboard(hotels: list[dict], tickets: list[dict] | None = None) -> InlineKeyboardMarkup | None:
    tickets = tickets or []
    if not hotels and not tickets:
        return None
    rows = []
    for hotel in hotels:
        name = hotel["name"]
        if len(name) > 28:
            name = name[:27] + "…"
        nights = hotel.get("nights") or 1
        if nights > 1:
            title = f"➕ {name} · {nights} н. ≈{hotel['price'] * nights} ₽"
            data = f"add:{hotel['id']}:{nights}"
        else:
            title = f"➕ {name} · ≈{hotel['price']} ₽"
            data = f"add:{hotel['id']}"
        rows.append([InlineKeyboardButton(text=title, callback_data=data)])
    for ticket in tickets:
        rows.append([InlineKeyboardButton(text="➕ " + ticket_title(ticket), callback_data=f"tk:{ticket['token']}")])
    if settings.webapp_url.startswith("https://"):
        rows.append(
            [
                InlineKeyboardButton(
                    text="🛒 Открыть корзину",
                    web_app=WebAppInfo(url=settings.webapp_url),
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(F.data.startswith("add:"))
async def on_add(callback: CallbackQuery) -> None:
    try:
        parts = callback.data.split(":")
        hotel_id = int(parts[1])
        nights = int(parts[2]) if len(parts) > 2 else 1
    except (ValueError, IndexError):
        await callback.answer("Не получилось добавить", show_alert=True)
        return

    item = await add_to_cart(callback.from_user.id, hotel_id, nights)
    if item is None:
        await callback.answer("Не получилось добавить. Попробуй /start", show_alert=True)
        return
    if item["already"]:
        await callback.answer(f"{item['name']} уже в корзине")
    else:
        await callback.answer(f"Добавила в корзину: {item['name']}")


@router.callback_query(F.data.startswith("tk:"))
async def on_add_ticket(callback: CallbackQuery) -> None:
    ticket = find_ticket(callback.from_user.id, callback.data.split(":", 1)[1])
    if ticket is None:
        await callback.answer("Предложение устарело, попроси Женю найти билеты ещё раз", show_alert=True)
        return
    item = await add_ticket(callback.from_user.id, ticket)
    if item is None:
        await callback.answer("Не получилось добавить. Попробуй /start", show_alert=True)
        return
    if item["already"]:
        await callback.answer(f"{item['name']} уже в корзине")
    else:
        await callback.answer(f"Добавила в корзину: {item['name']}")


async def _check_payment(query: PreCheckoutQuery) -> str | None:
    parts = (query.invoice_payload or "").split(":")
    if len(parts) != 3 or parts[0] != "cart":
        return "Не удалось проверить заказ. Оформи его заново в мини-аппе."
    try:
        owner, total = int(parts[1]), int(parts[2])
    except ValueError:
        return "Не удалось проверить заказ. Оформи его заново в мини-аппе."
    if owner != query.from_user.id or query.currency != "RUB":
        return "Не удалось проверить заказ. Оформи его заново в мини-аппе."
    cart = await get_cart(query.from_user.id)
    if not cart["items"] or cart["total"] != total or query.total_amount != total * 100:
        return "Корзина изменилась. Открой мини-апп и оформи заказ заново."
    return None


@router.pre_checkout_query()
async def on_pre_checkout(query: PreCheckoutQuery) -> None:
    error = await _check_payment(query)
    if error:
        await query.answer(ok=False, error_message=error)
    else:
        await query.answer(ok=True)


@router.message(F.successful_payment)
async def on_paid(message: Message) -> None:
    payment = message.successful_payment
    ref = payment.provider_payment_charge_id or payment.telegram_payment_charge_id
    order = await checkout(message.from_user.id, provider=PROVIDER_TELEGRAM, payment_ref=ref)
    if order is None:
        await message.answer(
            "Оплата прошла, но корзина оказалась пустой. Напиши нам, мы разберёмся."
        )
        return
    await message.answer(
        f"Оплата прошла (тестовый режим, деньги не списаны). Заказ {order['code']}, "
        f"сумма примерно {order['total']} ₽. Подробности в мини-аппе, вкладка «Корзина».",
        parse_mode=None,
    )
