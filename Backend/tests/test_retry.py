import asyncio

import pytest

from app.agent.retry import call_with_retry


class Flaky:
    def __init__(self, fails: int):
        self.fails, self.calls = fails, 0

    def __call__(self, value):
        self.calls += 1
        if self.calls <= self.fails:
            raise ConnectionError("503")
        return value * 2


def test_retries_then_succeeds():
    flaky = Flaky(fails=2)
    result = asyncio.run(call_with_retry(flaky, 21, retry_on=(ConnectionError,), delays=(0, 0)))
    assert result == 42 and flaky.calls == 3


def test_gives_up_after_last_attempt():
    flaky = Flaky(fails=10)
    with pytest.raises(ConnectionError):
        asyncio.run(call_with_retry(flaky, 1, retry_on=(ConnectionError,), delays=(0, 0)))
    assert flaky.calls == 3


def test_other_errors_are_not_retried():
    def broken(_):
        raise ValueError("bug")

    with pytest.raises(ValueError):
        asyncio.run(call_with_retry(broken, 1, retry_on=(ConnectionError,), delays=(0, 0)))
