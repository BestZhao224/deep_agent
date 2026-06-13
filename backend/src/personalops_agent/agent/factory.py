from __future__ import annotations

from langchain_core.tools import tool

from personalops_agent.agent.backend import create_project_backend
from personalops_agent.agent.prompts import MAIN_SYSTEM_PROMPT, TRAVEL_SYSTEM_PROMPT
from personalops_agent.config import Settings
from personalops_agent.tools.amap_mcp import load_amap_mcp_tools
from personalops_agent.tools.exchange import ExchangeRateTool
from personalops_agent.tools.search import SearchTool
from personalops_agent.tools.weather import WeatherTool


def build_search_tool(settings: Settings):
    search = SearchTool(settings)

    @tool
    async def search_web(query: str, locale: str = "zh-CN", max_results: int = 5) -> dict:
        """Search the public web for current information."""
        return (await search.search_web(query, locale, max_results)).model_dump()

    return search_web


async def build_coordinator_tools(settings: Settings):
    return [build_search_tool(settings)]


async def build_travel_tools(settings: Settings, mcp_loader=load_amap_mcp_tools):
    weather = WeatherTool(settings)
    exchange = ExchangeRateTool(settings)

    @tool
    async def get_weather(location: str, start_date: str, days: int = 3) -> dict:
        """Get real weather forecast for a destination."""
        return (await weather.get_weather(location, start_date, days)).model_dump()

    @tool
    async def convert_currency(amount: float, from_currency: str, to_currency: str) -> dict:
        """Convert currency using a real exchange-rate API."""
        return (await exchange.convert_currency(amount, from_currency, to_currency)).model_dump()

    amap_tools = await mcp_loader(settings)
    search_web = build_search_tool(settings)
    return [search_web, get_weather, convert_currency, *amap_tools]


async def create_personalops_agent(settings: Settings, checkpointer=None, backend=None):
    """Create the real DeepAgents graph.

    The imports stay inside the factory so tests and config validation do not pretend
    to run an agent when DeepAgents or credentials are missing.
    """
    settings.validate_llm_ready()

    try:
        from deepagents import create_deep_agent
        from langchain_openai import ChatOpenAI
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "DeepAgents runtime dependencies are not installed. Run `pip install -e .[dev]`."
        ) from exc

    model = ChatOpenAI(
        model=settings.deepseek_model,
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        temperature=0.4,
    )
    coordinator_tools = await build_coordinator_tools(settings)
    travel_tools = await build_travel_tools(settings)
    backend = backend or create_project_backend()
    subagents = [
        {
            "name": "travel-planner",
            "description": "规划旅行行程、预算、天气提醒、交通建议和装备清单。",
            "system_prompt": TRAVEL_SYSTEM_PROMPT,
            "tools": travel_tools,
        }
    ]
    return create_deep_agent(
        model=model,
        system_prompt=MAIN_SYSTEM_PROMPT,
        tools=coordinator_tools,
        subagents=subagents,
        backend=backend,
        checkpointer=checkpointer,
    )
