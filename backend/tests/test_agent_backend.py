import importlib
import sys
import types
from pathlib import Path

import pytest

from personalops_agent.agent import factory
from personalops_agent.config import Settings


def test_create_project_backend_points_at_backend_directory(monkeypatch):
    captured = {}

    class FakeFilesystemBackend:
        def __init__(self, *, root_dir, virtual_mode=False):
            captured["root_dir"] = root_dir
            captured["virtual_mode"] = virtual_mode

    monkeypatch.setitem(
        sys.modules,
        "deepagents.backends",
        types.SimpleNamespace(FilesystemBackend=FakeFilesystemBackend),
    )

    backend_module = importlib.import_module("personalops_agent.agent.backend")
    backend = backend_module.create_project_backend()

    assert backend is not None
    assert Path(captured["root_dir"]).name == "backend"
    assert captured["virtual_mode"] is True


@pytest.mark.asyncio
async def test_create_agent_passes_project_backend_to_deep_agent(monkeypatch):
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

    sentinel_backend = object()

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
    monkeypatch.setattr(factory, "create_project_backend", lambda: sentinel_backend, raising=False)

    agent = await factory.create_personalops_agent(
        Settings(deepseek_api_key="deepseek-secret", zhipu_api_key="zhipu-secret"),
        checkpointer=object(),
    )

    assert agent == "agent"
    assert captured["backend"] is sentinel_backend
    assert captured["tools"] == ["coordinator-search"]
    assert captured["subagents"][0]["tools"] == ["travel-search", "weather", "exchange", "amap"]
