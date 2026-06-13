from __future__ import annotations

import os
from typing import Self

from dotenv import load_dotenv
from pydantic import BaseModel, Field, model_validator

load_dotenv()


def env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


class Settings(BaseModel):
    """Runtime settings loaded from environment or tests."""

    app_env: str = Field(default_factory=lambda: os.getenv("APP_ENV", "development"))
    mongodb_uri: str = Field(default_factory=lambda: os.getenv("MONGODB_URI", ""))
    mongodb_db: str = Field(default_factory=lambda: os.getenv("MONGODB_DB", "personalops"))
    deepseek_api_key: str = Field(default_factory=lambda: os.getenv("DEEPSEEK_API_KEY", ""))
    deepseek_base_url: str = Field(
        default_factory=lambda: os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    )
    deepseek_model: str = Field(
        default_factory=lambda: os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    )
    zhipu_api_key: str = Field(default_factory=lambda: os.getenv("ZHIPU_API_KEY", ""))
    zhipu_base_url: str = Field(
        default_factory=lambda: os.getenv(
            "ZHIPU_BASE_URL",
            "https://open.bigmodel.cn/api/paas/v4/",
        )
    )
    weather_api_key: str = Field(default_factory=lambda: os.getenv("WEATHER_API_KEY", ""))
    weather_api_base_url: str = Field(
        default_factory=lambda: os.getenv("WEATHER_API_BASE_URL", "https://api.weatherapi.com")
    )
    exchange_rate_api_key: str = Field(
        default_factory=lambda: os.getenv("EXCHANGE_RATE_API_KEY", "")
    )
    exchange_rate_api_base_url: str = Field(
        default_factory=lambda: os.getenv(
            "EXCHANGE_RATE_API_BASE_URL",
            "https://v6.exchangerate-api.com",
        )
    )
    amap_maps_api_key: str = Field(default_factory=lambda: os.getenv("AMAP_MAPS_API_KEY", ""))
    amap_mcp_enabled: bool = Field(default_factory=lambda: env_bool("AMAP_MCP_ENABLED", True))
    amap_mcp_url: str = Field(
        default_factory=lambda: os.getenv("AMAP_MCP_URL", "https://mcp.amap.com/mcp")
    )
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            origin.strip()
            for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
            if origin.strip()
        ]
    )

    @model_validator(mode="after")
    def validate_storage_hint(self) -> Self:
        if not self.mongodb_uri and self.app_env == "production":
            raise ValueError("MONGODB_URI is required in production")
        return self

    def validate_llm_ready(self) -> Self:
        class LlmReady(BaseModel):
            deepseek_api_key: str = Field(min_length=1, alias="DEEPSEEK_API_KEY")
            deepseek_base_url: str = Field(min_length=1, alias="DEEPSEEK_BASE_URL")

        LlmReady(
            DEEPSEEK_API_KEY=self.deepseek_api_key,
            DEEPSEEK_BASE_URL=self.deepseek_base_url,
        )
        return self

    def missing_travel_tool_keys(self) -> list[str]:
        missing: list[str] = []
        if not self.zhipu_api_key:
            missing.append("ZHIPU_API_KEY")
        if not self.weather_api_key:
            missing.append("WEATHER_API_KEY")
        if not self.exchange_rate_api_key:
            missing.append("EXCHANGE_RATE_API_KEY")
        return missing

    def zhipu_web_search_url(self) -> str:
        return f"{self.zhipu_base_url.rstrip('/')}/web_search"

    def amap_mcp_server_config(self) -> dict[str, str]:
        return {
            "transport": "streamable_http",
            "url": self.amap_mcp_url.rstrip("/"),
        }


def get_settings() -> Settings:
    return Settings()
