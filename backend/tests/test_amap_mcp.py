import pytest

from personalops_agent.agent.factory import build_travel_tools
from personalops_agent.config import Settings
from personalops_agent.tools.amap_mcp import load_amap_mcp_tools, wrap_mcp_tool


@pytest.mark.asyncio
async def test_amap_mcp_loader_uses_streamable_http_url_without_api_key():
    class FakeTool:
        name = "maps_geo"
        description = "Geo"
        args_schema = {"type": "object", "properties": {}}

        async def ainvoke(self, args):
            return {"ok": True}

    class FakeClient:
        def __init__(self, config):
            self.config = config

        async def get_tools(self):
            assert self.config == {
                "amap-maps": {
                    "transport": "streamable_http",
                    "url": "https://mcp.api-inference.modelscope.net/dd01c51439bd41/mcp",
                }
            }
            return [FakeTool()]

    tools = await load_amap_mcp_tools(
        Settings(
            amap_maps_api_key="",
            amap_mcp_url="https://mcp.api-inference.modelscope.net/dd01c51439bd41/mcp",
            amap_mcp_enabled=True,
        ),
        client_cls=FakeClient,
    )

    assert [tool.name for tool in tools] == ["maps_geo"]


@pytest.mark.asyncio
async def test_amap_mcp_loader_returns_empty_only_when_explicitly_disabled():
    tools = await load_amap_mcp_tools(Settings(amap_mcp_enabled=False))

    assert tools == []


@pytest.mark.asyncio
async def test_amap_mcp_loader_retries_then_returns_unavailable_tool_when_client_fails():
    attempts = 0

    class FailingClient:
        def __init__(self, config):
            self.config = config

        async def get_tools(self):
            nonlocal attempts
            attempts += 1
            raise RuntimeError("Error parsing JSON response")

    tools = await load_amap_mcp_tools(
        Settings(
            amap_mcp_url="https://mcp.api-inference.modelscope.net/abc123/mcp",
            amap_mcp_enabled=True,
        ),
        client_cls=FailingClient,
        retries=2,
        retry_delay_seconds=0,
    )

    assert attempts == 3
    assert [tool.name for tool in tools] == ["amap_mcp_unavailable"]
    result = await tools[0].ainvoke({})
    assert result["ok"] is False
    assert "AMap MCP connection failed" in result["error"]


@pytest.mark.asyncio
async def test_amap_mcp_loaded_tool_returns_structured_error_when_call_fails():
    class FailingTool:
        name = "maps_geo"
        description = "Geo"
        args_schema = {"type": "object", "properties": {"address": {"type": "string"}}}

        async def ainvoke(self, args):
            raise RuntimeError("ENGINE_RESPONSE_DATA_ERROR")

    tool = wrap_mcp_tool(FailingTool())

    result = await tool.ainvoke({"address": "Beijing"})

    assert result["ok"] is False
    assert result["tool"] == "maps_geo"
    assert "ENGINE_RESPONSE_DATA_ERROR" in result["error"]


@pytest.mark.asyncio
async def test_build_travel_tools_includes_loaded_amap_mcp_tools():
    class FakeTool:
        name = "maps_geo"

    async def fake_loader(settings):
        assert settings.amap_mcp_url == "https://mcp.api-inference.modelscope.net/dd01c51439bd41/mcp"
        return [FakeTool()]

    tools = await build_travel_tools(
        Settings(
            amap_mcp_url="https://mcp.api-inference.modelscope.net/dd01c51439bd41/mcp",
            amap_mcp_enabled=True,
        ),
        mcp_loader=fake_loader,
    )

    assert any(getattr(tool, "name", None) == "maps_geo" for tool in tools)
