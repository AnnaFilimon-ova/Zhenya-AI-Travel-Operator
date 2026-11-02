import asyncio
from datetime import date, timedelta
from statistics import mean

import httpx

from app.providers.base import ProviderUnavailable

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
HEADERS = {"User-Agent": "ZhenyaTravelBot/0.1 (hackathon project)"}
FORECAST_DAYS = 16   
MAX_DAYS = 14        
CLIMATE_YEARS = 3
RAIN_MM = 1.0        

async def _fetch_daily(url: str, lat: float, lon: float, start: date, end: date) -> dict:
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "timezone": "auto",
    }
    try:
        async with httpx.AsyncClient(timeout=15, headers=HEADERS) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            return resp.json().get("daily") or {}
    except (httpx.HTTPError, ValueError) as exc:
        raise ProviderUnavailable(f"Open-Meteo: {type(exc).__name__}") from exc


def _stats(daily: dict) -> dict | None:
    tmax = [v for v in daily.get("temperature_2m_max") or [] if v is not None]
    tmin = [v for v in daily.get("temperature_2m_min") or [] if v is not None]
    rain = [v for v in daily.get("precipitation_sum") or [] if v is not None]
    if not tmax or not tmin:
        return None
    return {
        "tmax": mean(tmax),
        "tmin": mean(tmin),
        "rainy": sum(1 for v in rain if v >= RAIN_MM),
        "days": len(tmax),
    }


def _years_back(d: date, years: int) -> date:
    try:
        return d.replace(year=d.year - years)
    except ValueError:  
        return d.replace(year=d.year - years, day=28)


class OpenMeteoWeather:
    name = "open_meteo"

    async def summary(self, lat: float, lon: float, start: date, end: date) -> dict:
        end = min(end, start + timedelta(days=MAX_DAYS - 1))
        today = date.today()
        if start >= today and end <= today + timedelta(days=FORECAST_DAYS - 1):
            stats = _stats(await _fetch_daily(FORECAST_URL, lat, lon, start, end))
            source = "forecast"
            note = "Прогноз Open-Meteo, он может меняться."
        else:
            results = await asyncio.gather(
                *(
                    _fetch_daily(ARCHIVE_URL, lat, lon, _years_back(start, y), _years_back(end, y))
                    for y in range(1, CLIMATE_YEARS + 1)
                ),
                return_exceptions=True,
            )
            per_year = [s for s in (_stats(r) for r in results if isinstance(r, dict)) if s]
            stats = (
                {
                    "tmax": mean(s["tmax"] for s in per_year),
                    "tmin": mean(s["tmin"] for s in per_year),
                    "rainy": round(mean(s["rainy"] for s in per_year)),
                    "days": per_year[0]["days"],
                }
                if per_year
                else None
            )
            source = "climate"
            note = (
                "Прогноза на эти даты ещё нет. Значения усреднены по тем же датам "
                f"за последние {CLIMATE_YEARS} года: это обычная погода, а не прогноз."
            )
        if stats is None:
            raise ProviderUnavailable("Open-Meteo не вернул данных")
        return {
            "source": source,
            "period": [start.isoformat(), end.isoformat()],
            "days": stats["days"],
            "temp_max_avg": round(stats["tmax"]),
            "temp_min_avg": round(stats["tmin"]),
            "rainy_days": stats["rainy"],
            "note": note,
        }
