import pytest
from pydantic import ValidationError
from pathlib import Path

from personalops_agent.config import Settings, env_bool


def test_settings_requires_deepseek_key_for_llm_validation():
    settings = Settings(
        mongodb_uri="mongodb://localhost:27017",
        deepseek_api_key="",
        deepseek_base_url="https://api.deepseek.com",
    )

    with pytest.raises(ValidationError, match="DEEPSEEK_API_KEY"):
        settings.validate_llm_ready()


def test_settings_reports_missing_travel_tool_keys():
    settings = Settings(
        mongodb_uri="mongodb://localhost:27017",
        deepseek_api_key="sk-test",
        deepseek_base_url="https://api.deepseek.com",
        zhipu_api_key="",
        weather_api_key="",
        exchange_rate_api_key="",
    )

    assert settings.missing_travel_tool_keys() == [
        "ZHIPU_API_KEY",
        "WEATHER_API_KEY",
        "EXCHANGE_RATE_API_KEY",
    ]


def test_settings_builds_amap_mcp_streamable_http_url_without_leaking_key():
    settings = Settings(amap_mcp_url="https://mcp.api-inference.modelscope.net/abc123/mcp")

    config = settings.amap_mcp_server_config()

    assert config["transport"] == "streamable_http"
    assert config["url"] == "https://mcp.api-inference.modelscope.net/abc123/mcp"


def test_env_example_defaults_to_mongodb_storage():
    env_example = Path(__file__).resolve().parents[2] / ".env.example"

    assert "MONGODB_URI=mongodb://localhost:27017" in env_example.read_text(encoding="utf-8")


def test_env_example_enables_amap_mcp_by_default():
    env_example = Path(__file__).resolve().parents[2] / ".env.example"

    assert "AMAP_MCP_ENABLED=true" in env_example.read_text(encoding="utf-8")


def test_env_example_uses_streamable_http_amap_mcp_url():
    env_example = Path(__file__).resolve().parents[2] / ".env.example"

    assert (
        "AMAP_MCP_URL=https://mcp.api-inference.modelscope.net/<your-modelscope-mcp-id>/mcp"
        in env_example.read_text(encoding="utf-8")
    )


def test_amap_mcp_env_bool_defaults_to_enabled():
    assert env_bool("MISSING_BOOL_ENV", default=True) is True
