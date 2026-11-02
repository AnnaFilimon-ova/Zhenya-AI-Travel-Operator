import asyncio
import logging
from collections.abc import Callable
from typing import Any

log = logging.getLogger(__name__)

DEFAULT_DELAYS = (2.0, 5.0)


async def call_with_retry(
    func: Callable[..., Any],
    *args: Any,
    retry_on: tuple[type[BaseException], ...],
    delays: tuple[float, ...] = DEFAULT_DELAYS,
) -> Any:
    for attempt, delay in enumerate((*delays, None), start=1):
        try:
            return await asyncio.to_thread(func, *args)
        except retry_on as exc:
            if delay is None:
                raise
            log.warning("Попытка %s не удалась (%s), повтор через %s с", attempt, type(exc).__name__, delay)
            await asyncio.sleep(delay)
