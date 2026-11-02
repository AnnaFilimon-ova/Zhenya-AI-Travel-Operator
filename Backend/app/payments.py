"""Провайдеры оплаты. Агент и корзина знают только интерфейс PaymentProvider.

Сейчас два варианта:
- DemoPayments: имитация, заказ создаётся сразу (когда токен ЮKassa не задан);
- TelegramInvoicePayments: счёт Telegram Payments через ЮKassa. С тестовым токеном
  (формат 123456:TEST:789) деньги не списываются. С боевым токеном те же вызовы работают всерьёз.
Чтобы подключить другого провайдера, достаточно написать ещё один класс с методом start().
"""
import json
from typing import Protocol

from aiogram import Bot
from aiogram.types import LabeledPrice

from app.cart import checkout
from app.config import settings

PROVIDER_DEMO = "demo"
PROVIDER_TELEGRAM = "telegram_yookassa"


class PaymentProvider(Protocol):
    name: str

    async def start(self, telegram_id: int, cart: dict) -> dict:
        """Начинает оплату непустой корзины. Возвращает словарь для мини-аппа."""
        ...


class DemoPayments:
    name = PROVIDER_DEMO

    async def start(self, telegram_id: int, cart: dict) -> dict:
        order = await checkout(telegram_id, provider=self.name)
        return {"mode": "demo", "order": order}


def _label(item: dict) -> str:
    if item.get("type") == "ticket":
        return item["name"]
    return f"{item['name']}, {item['nights']} н."


class TelegramInvoicePayments:
    name = PROVIDER_TELEGRAM

    def __init__(self, provider_token: str) -> None:
        self.provider_token = provider_token

    async def start(self, telegram_id: int, cart: dict) -> dict:
        items = cart["items"]
        prices = [
            LabeledPrice(
                label=_label(item)[:60],
                amount=item["subtotal"] * 100,  # Telegram принимает копейки
            )
            for item in items
        ]
        receipt = {
            "items": [
                {
                    "description": _label(item)[:128],
                    "quantity": "1.00",
                    "amount": {"value": f"{item['subtotal']:.2f}", "currency": "RUB"},
                    "vat_code": 1,
                    "payment_mode": "full_payment",
                    "payment_subject": "service",
                }
                for item in items
            ]
        }
        bot = Bot(token=settings.bot_token)
        try:
            url = await bot.create_invoice_link(
                title="Поездка с Женей",
                description="Тестовая оплата: деньги не списываются. Цены оценочные.",
                payload=f"cart:{telegram_id}:{cart['total']}",
                provider_token=self.provider_token,
                currency="RUB",
                prices=prices,
                need_email=True,
                send_email_to_provider=True,
                provider_data=json.dumps({"receipt": receipt}, ensure_ascii=False),
            )
        finally:
            await bot.session.close()
        return {"mode": "invoice", "url": url}


def get_provider() -> PaymentProvider:
    token = (settings.payment_provider_token or "").strip()
    if token:
        return TelegramInvoicePayments(token)
    return DemoPayments()
