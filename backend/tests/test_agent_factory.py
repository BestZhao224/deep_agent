import sys
import types

import pytest

from personalops_agent.agent import factory
from personalops_agent.agent.memory import create_short_term_checkpointer
from personalops_agent.config import Settings


def test_create_short_term_checkpointer_returns_reusable_instance():
    checkpointer = create_short_term_checkpointer()

    assert checkpointer is not None


@pytest.mark.asyncio
async def test_coordinator_tools_only_include_web_search():
    tools = await factory.build_coordinator_tools(Settings(zhipu_api_key="zhipu-secret"))

    assert [tool.name for tool in tools] == ["search_web"]


@pytest.mark.asyncio
async def test_create_agent_gives_main_and_travel_subagent_different_tool_sets(monkeypatch):
    captured = {}

    class FakeChatOpenAI:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    def fake_create_deep_agent(**kwargs):
        captured.update(kwargs)
        return "agent"

    async def fake_build_coordinator_tools(settings):
        return ["coordinator-search"]

    async def fake_build_travel_tools(settings):
        return ["travel-search", "weather", "exchange", "amap"]

    monkeypatch.setitem(
        sys.modules,
        "deepagents",
        types.SimpleNamespace(create_deep_agent=fake_create_deep_agent),
    )
    monkeypatch.setitem(
        sys.modules,
        "langchain_openai",
        types.SimpleNamespace(ChatOpenAI=FakeChatOpenAI),
    )
    monkeypatch.setattr(factory, "build_coordinator_tools", fake_build_coordinator_tools)
    monkeypatch.setattr(factory, "build_travel_tools", fake_build_travel_tools)

    checkpointer = object()
    agent = await factory.create_personalops_agent(
        Settings(deepseek_api_key="deepseek-secret", zhipu_api_key="zhipu-secret"),
        checkpointer=checkpointer,
    )

    assert agent == "agent"
    assert captured["checkpointer"] is checkpointer
    assert captured["tools"] == ["coordinator-search"]
    assert captured["subagents"][0]["tools"] == ["travel-search", "weather", "exchange", "amap"]
