import pytest

from app.agent import service
from app.providers.transport import flight_link


@pytest.fixture(autouse=True)
def clean():
    service._offered_tickets.clear()
    service._ticket_cache.clear()


OPTIONS = [
    {"id": "MOW-AER-2026-12-15-4199", "mode": "plane", "origin": "MOW", "destination": "AER", "price_rub": 4199},
    {"id": "train-Москва-Сочи-coupe", "mode": "train", "origin": "Москва", "destination": "Сочи", "price_rub": 9000},
]


def test_offered_tickets_are_popped_but_stay_findable():
    service.remember_tickets(5, OPTIONS)
    offered = service.pop_offered_tickets(5)
    assert [t["origin"] for t in offered] == ["Москва", "Москва"]
    assert service.pop_offered_tickets(5) == []
    token = service.ticket_token(OPTIONS[0]["id"])
    assert len(token) == 10 and service.find_ticket(5, token)["price_rub"] == 4199
    assert service.find_ticket(6, token) is None
    assert service.find_ticket(5, "unknown") is None


def test_callback_data_fits_telegram_limit():
    assert len(("tk:" + service.ticket_token("x" * 500)).encode()) <= 64


def test_ticket_cache_is_bounded():
    many = [{"id": f"id-{i}", "mode": "plane", "origin": "MOW", "destination": "LED", "price_rub": i} for i in range(100)]
    service.remember_tickets(5, many)
    assert len(service._ticket_cache[5]) == service.TICKET_CACHE_MAX


def test_flight_link_format():
    assert flight_link("MOW", "AER", "2026-12-15T09:15:00+03:00") == "https://www.aviasales.ru/search/MOW1512AER1"
    assert flight_link("MOW", "AER", None) == ""
    assert flight_link("MOW", "AER", "15 декабря") == ""


def test_keyboard_has_ticket_buttons_and_cart_button(monkeypatch):
    from app.bot.handlers import cart as handler

    monkeypatch.setattr(handler.settings, "webapp_url", "https://example.com")
    service.remember_tickets(5, OPTIONS)
    tickets = service.pop_offered_tickets(5)
    keyboard = handler.offered_keyboard([], tickets)
    texts = [row[0].text for row in keyboard.inline_keyboard]
    assert texts[0].startswith("➕ ✈️ Москва → Сочи") and "4199" in texts[0]
    assert texts[1].startswith("➕ 🚆") and texts[-1] == "🛒 Открыть корзину"
    callbacks = [row[0].callback_data for row in keyboard.inline_keyboard if row[0].callback_data]
    assert all(c.startswith("tk:") and len(c.encode()) <= 64 for c in callbacks)
    assert handler.offered_keyboard([], []) is None
    assert handler.offered_keyboard([{"id": 1, "name": "Отель", "price": 4000}], None) is not None


def test_instruction_asks_to_mention_approximate_data_only_once():
    text = service.build_instruction({}, ["Москва"])
    assert "DISCLAIMERS" in text and "ONCE per conversation" in text
    assert "this is a demo, no real payment" not in text
