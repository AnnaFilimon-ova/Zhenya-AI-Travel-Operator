import asyncio
import sys
from datetime import date
from pathlib import Path
from app.memory import load_history  # noqa: E402
from dotenv import load_dotenv
from google import genai
from google.genai import types
from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[3]
load_dotenv(ROOT / "Backend" / ".env")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Agent.tools import filter_hotels, format_hotel_results, search_hotels  # noqa: E402

from app.config import settings  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from app.models import User  # noqa: E402

MODEL = "gemini-3.6-flash"
client = genai.Client(api_key=settings.gemini_api_key)
_chats: dict[int, object] = {}


def search_hotels_for_agent(
    location: str,
    check_in: str,
    check_out: str,
    adults: int,
    children: int,
    children_ages: list[int],
    min_price: float,
    max_price: float,
    pets_allowed: bool,
    accessibility: list[str],
    min_rating: float | None = None,
    required_amenities: list[str] | None = None,
):
    """Search hotels and filter them. Dates in YYYY-MM-DD format."""
    data = search_hotels(
        location=location,
        check_in=check_in,
        check_out=check_out,
        adults=adults,
        children=children,
        children_ages=children_ages,
        min_price=None,
        max_price=None,
        pets_allowed=pets_allowed,
        accessibility=accessibility,
    )
    results = format_hotel_results(data)
    results["hotels"] = filter_hotels(
        hotels=results["hotels"],
        min_price=min_price,
        max_price=max_price,
        min_rating=min_rating,
        required_amenities=required_amenities,
        pets_allowed=True if pets_allowed else None,
    )
    return results


def filter_hotels_for_agent(
    hotels: list[dict],
    min_price: float | None = None,
    max_price: float | None = None,
    min_rating: float | None = None,
    required_amenities: list[str] | None = None,
    pets_allowed: bool | None = None,
):
    """Apply extra filters to a hotel list returned by the search."""
    return filter_hotels(
        hotels=hotels,
        min_price=min_price,
        max_price=max_price,
        min_rating=min_rating,
        required_amenities=required_amenities,
        pets_allowed=pets_allowed,
    )


def build_instruction(profile: dict) -> str:
    name = profile.get("name") or "unknown"
    language = profile.get("language") or "ru"
    return f"""
You are Zhenya, an AI travel and hotel assistant in a Telegram bot.
Today's date: {date.today().isoformat()}.
User name: {name}. Preferred language: {language}.
Always reply in the language the user writes in. Keep answers short and friendly.
Plain text only: no markdown, no asterisks, no tables.

HOTEL SEARCH RULES:
- To find or compare accommodation, use search_hotels_for_agent.
- Collect: destination, check-in and check-out dates, number of adults and
  children, children's ages, min and max nightly budget, pet and accessibility needs.
- If required information is missing, ask for it. Never invent hotel data.
- Pass children_ages=[] and accessibility=[] when there are none.
- Never silently drop a user's requirement.
- Use filter_hotels_for_agent for extra filters (rating, amenities) and pass
  the real hotel list from the search.
- Missing pet or accessibility info means unknown, not confirmed or denied.
- Results may be sandbox sample data, not live availability. Say so clearly.
- State the currency exactly as returned.
- For general travel questions, answer normally without searching.
""".strip()


def to_contents(history: list[dict]) -> list[types.Content]:
    return [
        types.Content(role=item["role"], parts=[types.Part(text=item["text"])])
        for item in history
    ]


def to_contents(history: list[dict]) -> list[types.Content]:
    return [
        types.Content(role=item["role"], parts=[types.Part(text=item["text"])])
        for item in history
    ]


def create_chat(profile: dict, history: list[types.Content] | None = None):
    return client.chats.create(
        model=MODEL,
        history=history or [],
        config=types.GenerateContentConfig(
            tools=[search_hotels_for_agent, filter_hotels_for_agent],
            system_instruction=build_instruction(profile),
        ),
    )


async def get_profile(telegram_id: int) -> dict:
    async with SessionLocal() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
    if user is None:
        return {}
    return {
        "name": user.display_name or user.first_name,
        "language": user.language,
    }


_locks: dict[int, asyncio.Lock] = {}


def forget_chat(telegram_id: int) -> None:
    _chats.pop(telegram_id, None)


async def ask(telegram_id: int, text: str) -> str:
    lock = _locks.setdefault(telegram_id, asyncio.Lock())
    async with lock:
        chat = _chats.get(telegram_id)
        if chat is None:
            profile = await get_profile(telegram_id)
            history = await load_history(telegram_id)
            chat = create_chat(profile, to_contents(history))
            _chats[telegram_id] = chat
        response = await asyncio.to_thread(chat.send_message, text)
        return response.text or "Не получилось сформулировать ответ, попробуй переписать запрос."
async def welcome_back(telegram_id: int) -> str | None:
    history = await load_history(telegram_id, limit=10)
    if not history:
        return None

    profile = await get_profile(telegram_id)
    name = profile.get("name") or "the user"
    dialog = "\n".join(
        f"{'User' if item['role'] == 'user' else 'Zhenya'}: {item['text'][:300]}"
        for item in history
    )
    prompt = f"""
You are Zhenya, a friendly AI travel assistant in a Telegram bot.
The user {name} just pressed /start again. Here is their recent conversation:

{dialog}

Write 1-2 short warm sentences in the language of the conversation:
welcome them back, mention specifically what they were planning
(destination, dates, guests, if known), and offer to continue.
Add that they can send /reset to start over.
Do not invent details that are not in the conversation.
If the conversation contains no travel plans, just welcome them back warmly.
Plain text, no markdown, at most one emoji.
""".strip()

    try:
        response = await asyncio.to_thread(
            client.models.generate_content, model=MODEL, contents=prompt
        )
    except Exception:
        return None
    return (response.text or "").strip() or None