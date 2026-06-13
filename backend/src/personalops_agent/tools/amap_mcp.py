from __future__ import annotations

import asyncio
import logging

from langchain_core.tools import StructuredTool

from personalops_agent.config import Settings

logger = logging.getLogger(__name__)


def _build_error_message(exc: Exception) -> str:
    return f"AMap MCP connection failed: {exc}"


def unavailable_mcp_tool(error: str) -> StructuredTool:
    async def amap_mcp_unavailable() -> dict:
        """Report why AMap MCP tools are unavailable."""
        return {
            "ok": False,
            "tool": "amap_mcp",
            "error": error,
            "suggestion": "AMap MCP is temporarily unavailable. Continue with web search and configured local tools.",
        }

    return StructuredTool.from_function(
        coroutine=amap_mcp_unavailable,
        name="amap_mcp_unavailable",
        description="Report that AMap MCP tools are currently unavailable and explain why.",
    )


def wrap_mcp_tool(mcp_tool) -> StructuredTool:
    async def safe_mcp_tool(**kwargs) -> dict:
        try:
            return await mcp_tool.ainvoke(kwargs)
        except Exception as exc:
            logger.warning(
                "AMap MCP tool call failed: %s: %s",
                getattr(mcp_tool, "name", "unknown"),
                exc,
            )
            return {
                "ok": False,
                "tool": getattr(mcp_tool, "name", "unknown"),
                "error": str(exc),
                "suggestion": "Use other available tools or explain that this AMap MCP call failed.",
            }

    return StructuredTool(
        name=mcp_tool.name,
        description=getattr(mcp_tool, "description", ""),
        args_schema=getattr(mcp_tool, "args_schema", {"type": "object", "properties": {}}),
        coroutine=safe_mcp_tool,
    )


async def load_amap_mcp_tools(
    settings: Settings,
    client_cls=None,
    retries: int = 2,
    retry_delay_seconds: float = 0.5,
):
    """Load AMap MCP tools from the configured streamable_http endpoint."""
    if not settings.amap_mcp_enabled:
        return []

    if not settings.amap_mcp_url.strip():
        return [unavailable_mcp_tool("AMap MCP connection failed: AMAP_MCP_URL is not configured")]

    try:
        if client_cls is None:
            from langchain_mcp_adapters.client import MultiServerMCPClient

            client_cls = MultiServerMCPClient
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "AMap MCP requires langchain-mcp-adapters. Run `pip install -e .[dev]`."
        ) from exc

    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            client = client_cls({"amap-maps": settings.amap_mcp_server_config()})
            tools = await client.get_tools()
            return [wrap_mcp_tool(tool) for tool in tools]
        except Exception as exc:
            last_error = exc
            logger.warning("AMap MCP tool loading failed on attempt %s: %s", attempt + 1, exc)
            if attempt < retries:
                await asyncio.sleep(retry_delay_seconds)

    assert last_error is not None
    return [unavailable_mcp_tool(_build_error_message(last_error))]
