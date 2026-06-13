from __future__ import annotations

from pydantic import BaseModel, Field


class SearchItem(BaseModel):
    title: str
    url: str
    snippet: str = ""


class SearchResult(BaseModel):
    ok: bool
    items: list[SearchItem] = Field(default_factory=list)
    error: str | None = None


class WeatherForecast(BaseModel):
    date: str
    condition: str
    min_c: float | None = None
    max_c: float | None = None


class WeatherResult(BaseModel):
    ok: bool
    forecasts: list[WeatherForecast] = Field(default_factory=list)
    error: str | None = None


class ExchangeRateResult(BaseModel):
    ok: bool
    amount: float
    from_currency: str
    to_currency: str
    converted_amount: float | None = None
    rate: float | None = None
    error: str | None = None
