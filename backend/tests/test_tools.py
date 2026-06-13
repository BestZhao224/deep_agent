import pytest

from personalops_agent.config import Settings
from personalops_agent.tools.exchange import ExchangeRateTool
from personalops_agent.tools.search import SearchTool
from personalops_agent.tools.weather import WeatherTool


@pytest.mark.asyncio
async def test_search_tool_refuses_to_fake_results_without_api_key():
    tool = SearchTool(Settings(zhipu_api_key=""))

    result = await tool.search_web("东京 美食", locale="zh-CN", max_results=3)

    assert result.ok is False
    assert "ZHIPU_API_KEY" in result.error
    assert result.items == []


@pytest.mark.asyncio
async def test_search_tool_parses_zhipu_web_search_response():
    captured = {}

    async def fake_post(url, headers, json):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json

        class Response:
            def raise_for_status(self):
                return None

            def json(self):
                return {
                    "search_result": [
                        {
                            "title": "东京美食指南",
                            "link": "https://example.com/tokyo-food",
                            "content": "拉面、寿司和居酒屋路线。",
                        }
                    ]
                }

        return Response()

    tool = SearchTool(Settings(zhipu_api_key="zhipu-secret"))

    result = await tool.search_web("东京 美食", locale="zh-CN", max_results=3, post=fake_post)

    assert result.ok is True
    assert result.items[0].title == "东京美食指南"
    assert result.items[0].url == "https://example.com/tokyo-food"
    assert captured["url"] == "https://open.bigmodel.cn/api/paas/v4/web_search"
    assert captured["headers"]["Authorization"] == "Bearer zhipu-secret"
    assert captured["json"]["search_engine"] == "search_std"
    assert captured["json"]["search_query"] == "东京 美食"
    assert captured["json"]["count"] == 3


@pytest.mark.asyncio
async def test_search_tool_raises_for_real_http_errors():
    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, url, headers, json):
            class Response:
                def raise_for_status(self):
                    raise RuntimeError("http error")

                def json(self):
                    return {}

            return Response()

    tool = SearchTool(Settings(zhipu_api_key="zhipu-secret"))

    with pytest.raises(RuntimeError, match="http error"):
        await tool.search_web("东京", client_factory=lambda **kwargs: FakeClient())


@pytest.mark.asyncio
async def test_weather_tool_refuses_to_fake_results_without_api_key():
    tool = WeatherTool(Settings(weather_api_key=""))

    result = await tool.get_weather("Tokyo", start_date="2026-07-01", days=3)

    assert result.ok is False
    assert "WEATHER_API_KEY" in result.error
    assert result.forecasts == []


@pytest.mark.asyncio
async def test_exchange_tool_refuses_to_fake_results_without_api_key():
    tool = ExchangeRateTool(Settings(exchange_rate_api_key=""))

    result = await tool.convert_currency(100, "USD", "CNY")

    assert result.ok is False
    assert "EXCHANGE_RATE_API_KEY" in result.error
    assert result.converted_amount is None
