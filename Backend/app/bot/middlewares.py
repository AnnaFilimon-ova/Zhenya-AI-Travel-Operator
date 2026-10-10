import time
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, delay: float = 5.0) -> None:
        self.delay = delay
        self.last_message: dict[int, float] = {}
        self.warned: set[int] = set()

    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        user_id = event.from_user.id

        state = data.get("state")
        if state is not None and await state.get_state() is not None:
            return await handler(event, data)

        now = time.monotonic()
        last = self.last_message.get(user_id)

        if last is not None and now - last < self.delay:
            if user_id not in self.warned:
                self.warned.add(user_id)
                wait = int(self.delay - (now - last)) + 1
                await event.answer(f"Не так быстро 🙂 Подожди {wait} сек.")
            return

        self.last_message[user_id] = now
        self.warned.discard(user_id)
        return await handler(event, data)