import asyncio
from datetime import date, timedelta

import pytest

from app.providers import weather as w
from app.providers.base import ProviderUnavailable


def daily(days, tmax, tmin, rain):
    return {
        "time": [f"d{i}" for i in range(days)],
        "temperature_2m_max": [tmax] * days,
        "temperature_2m_min": [tmin] * days,
        "precipitation_sum": rain,
    }


def run(coro):
    return asyncio.run(coro)


def test_stats_skips_missing_values_and_counts_rainy_days():
    s = w._stats({"temperature_2m_max": [10, None, 14], "temperature_2m_min": [2, 4, None],
                  "precipitation_sum": [0, 0.5, 3.0, None]})
    assert s["tmax"] == 12 and s["tmin"] == 3 and s["rainy"] == 1 and s["days"] == 2
    assert w._stats({}) is None


def test_near_dates_use_forecast(monkeypatch):
    calls = []

    async def fake(url, lat, lon, start, end):
        calls.append(url)
        return daily(3, 8, 1, [0, 2, 0])

    monkeypatch.setattr(w, "_fetch_daily", fake)
    start = date.today() + timedelta(days=2)
    result = run(w.OpenMeteoWeather().summary(55.0, 37.0, start, start + timedelta(days=2)))
    assert calls == [w.FORECAST_URL]
    assert result["source"] == "forecast"
    assert (result["temp_max_avg"], result["temp_min_avg"], result["rainy_days"]) == (8, 1, 1)


def test_far_dates_use_climate_of_previous_years(monkeypatch):
    calls = []

    async def fake(url, lat, lon, start, end):
        calls.append((url, start.year))
        return daily(3, 20, 12, [0, 0, 0])

    monkeypatch.setattr(w, "_fetch_daily", fake)
    start = date.today() + timedelta(days=60)
    result = run(w.OpenMeteoWeather().summary(43.5, 39.7, start, start + timedelta(days=2)))
    assert result["source"] == "climate"
    assert "не прогноз" in result["note"]
    assert sorted(y for _, y in calls) == [start.year - 3, start.year - 2, start.year - 1]
    assert all(url == w.ARCHIVE_URL for url, _ in calls)


def test_climate_survives_one_failed_year_but_not_all(monkeypatch):
    state = {"n": 0}

    async def flaky(url, lat, lon, start, end):
        state["n"] += 1
        if state["n"] == 1:
            raise ProviderUnavailable("down")
        return daily(2, 10, 5, [0, 0])

    monkeypatch.setattr(w, "_fetch_daily", flaky)
    start = date.today() + timedelta(days=60)
    assert run(w.OpenMeteoWeather().summary(1, 1, start, start + timedelta(days=1)))["temp_max_avg"] == 10

    async def dead(*args):
        raise ProviderUnavailable("down")

    monkeypatch.setattr(w, "_fetch_daily", dead)
    with pytest.raises(ProviderUnavailable):
        run(w.OpenMeteoWeather().summary(1, 1, start, start + timedelta(days=1)))


def test_long_period_is_cut_and_leap_day_is_handled(monkeypatch):
    seen = []

    async def fake(url, lat, lon, start, end):
        seen.append((start, end))
        return daily((end - start).days + 1, 5, 0, [])

    monkeypatch.setattr(w, "_fetch_daily", fake)
    start = date.today() + timedelta(days=100)
    result = run(w.OpenMeteoWeather().summary(1, 1, start, start + timedelta(days=60)))
    assert result["days"] == w.MAX_DAYS
    assert w._years_back(date(2028, 2, 29), 1) == date(2027, 2, 28)
