from __future__ import annotations

import httpx

from personalops_agent.config import Settings
from personalops_agent.tools.models import WeatherForecast, WeatherResult


class WeatherTool:
    """WeatherAPI-compatible forecast wrapper."""

    def __init__(self, settings: Settings):
        self.settings = settings

    async def get_weather(self, location: str, start_date: str, days: int = 3) -> WeatherResult:
        if not self.settings.weather_api_key:
            return WeatherResult(
                ok=False,
                error=(
                    "WEATHER_API_KEY is required for real weather lookup; "
                    "no fake results returned."
                ),
            )

        url = f"{self.settings.weather_api_base_url.rstrip('/')}/v1/forecast.json"
        params = {
            "key": self.settings.weather_api_key,
            "q": location,
            "days": days,
            "aqi": "no",
            "alerts": "no",
        }
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        forecasts = []
        for item in data.get("forecast", {}).get("forecastday", []):
            day = item.get("day", {})
            forecasts.append(
                WeatherForecast(
                    date=item.get("date", start_date),
                    condition=day.get("condition", {}).get("text", ""),
                    min_c=day.get("mintemp_c"),
                    max_c=day.get("maxtemp_c"),
                )
            )
        return WeatherResult(ok=True, forecasts=forecasts)
