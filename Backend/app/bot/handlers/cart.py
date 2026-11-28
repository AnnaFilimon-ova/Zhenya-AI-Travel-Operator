
"""Кнопки «добавить в корзину» под ответом бота."""

from aiogram import F, Router
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    PreCheckoutQuery,
    WebAppInfo,
)

from app.cart import add_to_cart, checkout, get_cart
from app.config import settings
from app.payments import PROVIDER_TELEGRAM

router = Router()


def offered_keyboard(hotels: list[dict]) -> InlineKeyboardMarkup | None:
    """Клавиатура для предложенных отелей и авиабилетов."""

    if not hotels:
        return None

    rows = []

    for hotel in hotels:
        # Авиабилеты определяем по наличию токена предложения.
        if "token" in hotel:
            origin = hotel.get("origin", "?")
            destination = hotel.get("destination", "?")
            price = hotel.get("price_rub", 0)
            depart_at = hotel.get("depart_at", "")

            title = f"✈️ {origin} → {destination}"

            if depart_at:
                title += f" · {depart_at}"

            if price:
                title += f" · ≈{price} ₽"

            # Для билетов открываем страницу поиска Aviasales.
            url = hotel.get("url", "")

            if url.startswith("https://"):
                rows.append([
                    InlineKeyboardButton(
                        text=title[:64],
                        url=url,
                    )
                ])

            continue

        # Для отелей сохраняем прежнее поведение.
        name = hotel["name"]

        if len(name) > 28:
            name = name[:27] + "…"

        title = f"➕ {name} · ≈{hotel['price']} ₽"

        rows.append([
            InlineKeyboardButton(
                text=title,
                callback_data=f"add:{hotel['id']}",
            )
        ])

    # Telegram принимает для мини-аппа только https-адреса.
    if settings.webapp_url.startswith("https://"):
        rows.append([
            InlineKeyboardButton(
                text="🛒 Открыть корзину",
                web_app=WebAppInfo(url=settings.webapp_url),
            )
        ])

    if not rows:
        return None

    return InlineKeyboardMarkup(inline_keyboard=rows)

@router.callback_query(F.data.startswith("add:"))
async def on_add(callback: CallbackQuery) -> None:
    try:
        hotel_id = int(callback.data.split(":", 1)[1])
    except ValueError:
        await callback.answer("Не получилось добавить", show_alert=True)
        return

    item = await add_to_cart(callback.from_user.id, hotel_id)

    if item is None:
        await callback.answer(
            "Не получилось добавить. Попробуй /start",
            show_alert=True,
        )
        return

    if item["already"]:
        await callback.answer(f"{item['name']} уже в корзине")
    else:
        await callback.answer(f"Добавила в корзину: {item['name']}")


async def _check_payment(query: PreCheckoutQuery) -> str | None:
    """None, если платёж можно принять, иначе текст ошибки для пользователя."""
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

    if (
        not cart["items"]
        or cart["total"] != total
        or query.total_amount != total * 100
    ):
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

    order = await checkout(
        message.from_user.id,
        provider=PROVIDER_TELEGRAM,
        payment_ref=ref,
    )

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
