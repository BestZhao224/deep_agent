from __future__ import annotations

from pydantic import BaseModel, Field


class TravelDay(BaseModel):
    day: int = Field(ge=1)
    theme: str
    morning: str
    afternoon: str
    evening: str


class TravelBudget(BaseModel):
    currency: str = Field(min_length=3, max_length=3)
    total: float = Field(ge=0)


class TravelPlan(BaseModel):
    destination: str
    summary: str
    days: list[TravelDay] = Field(default_factory=list)
    estimated_budget: TravelBudget
    weather_notes: list[str] = Field(default_factory=list)
    transport_tips: list[str] = Field(default_factory=list)
    packing_checklist: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
