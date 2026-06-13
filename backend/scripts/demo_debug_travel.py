from __future__ import annotations

import asyncio
import json
import sys
import textwrap
from pathlib import Path
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = BACKEND_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from deepagents import create_deep_agent
from langchain.agents.middleware.types import AgentMiddleware
from langchain_core.messages import AIMessage, BaseMessage
from langchain.tools.tool_node import ToolCallRequest
from langchain_openai import ChatOpenAI
from langgraph.types import Command

from personalops_agent.agent.factory import build_coordinator_tools, build_travel_tools
from personalops_agent.agent.prompts import MAIN_SYSTEM_PROMPT, TRAVEL_SYSTEM_PROMPT
from personalops_agent.config import Settings


TARGET_PROMPT = "帮我规划一个 5 天东京旅行，预算 10w 人民币，偏美食和城市漫步"


def hr(title: str) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def short_json(value: Any, limit: int = 1800) -> str:
    try:
        text = json.dumps(value, ensure_ascii=False, indent=2, default=str)
    except TypeError:
        text = str(value)
    if len(text) > limit:
        return text[:limit] + "\n...<truncated>..."
    return text


def render_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    return short_json(content, limit=1200)


def describe_message(msg: BaseMessage) -> str:
    lines = [f"- {msg.__class__.__name__}(type={getattr(msg, 'type', 'unknown')})"]
    content = getattr(msg, "content", None)
    if content:
        lines.append(f"  content: {render_content(content)}")
    tool_calls = getattr(msg, "tool_calls", None)
    if tool_calls:
        lines.append(f"  tool_calls: {short_json(tool_calls, limit=1200)}")
    invalid_tool_calls = getattr(msg, "invalid_tool_calls", None)
    if invalid_tool_calls:
        lines.append(f"  invalid_tool_calls: {short_json(invalid_tool_calls, limit=1200)}")
    name = getattr(msg, "name", None)
    if name:
        lines.append(f"  name: {name}")
    tool_call_id = getattr(msg, "tool_call_id", None)
    if tool_call_id:
        lines.append(f"  tool_call_id: {tool_call_id}")
    return "\n".join(lines)


def describe_messages(messages: list[BaseMessage]) -> str:
    if not messages:
        return "  (no messages)"
    return "\n".join(describe_message(msg) for msg in messages)


def describe_tools(tools: list[Any]) -> str:
    if not tools:
        return "  (no tools)"
    chunks = []
    for index, tool in enumerate(tools, start=1):
        name = getattr(tool, "name", type(tool).__name__)
        description = getattr(tool, "description", "")
        description = " ".join(str(description).split())
        if len(description) > 220:
            description = description[:220] + "..."
        chunks.append(f"  {index}. {name}: {description}")
    return "\n".join(chunks)


def describe_result(result: Any) -> str:
    if isinstance(result, Command):
        return f"Command(update={short_json(getattr(result, 'update', {}), limit=1600)})"
    if isinstance(result, AIMessage):
        return describe_message(result)
    if isinstance(result, BaseMessage):
        return describe_message(result)
    return short_json(result, limit=1600)


class ConsoleTraceMiddleware(AgentMiddleware):
    def __init__(self, label: str):
        super().__init__()
        self.label = label
        self._model_calls = 0
        self._tool_calls = 0

    @property
    def name(self) -> str:
        return f"ConsoleTrace[{self.label}]"

    async def awrap_model_call(self, request, handler):
        self._model_calls += 1
        call_no = self._model_calls
        hr(f"[{self.label}] MODEL CALL #{call_no}")
        if request.system_message is not None:
            print("[system_message]")
            print(render_content(request.system_message.content))
        else:
            print("[system_message] (none)")
        print("[messages]")
        print(describe_messages(request.messages))
        print("[tools]")
        print(describe_tools(list(request.tools)))
        response = await handler(request)
        print("[model_response]")
        print(f"  structured_response: {render_content(getattr(response, 'structured_response', None))}")
        print("  messages:")
        for msg in getattr(response, "result", []):
            print(textwrap.indent(describe_message(msg), "    "))
        return response

    async def awrap_tool_call(self, request: ToolCallRequest, handler):
        self._tool_calls += 1
        call_no = self._tool_calls
        hr(f"[{self.label}] TOOL CALL #{call_no}")
        tool_name = request.tool_call.get("name", "unknown")
        print(f"[tool_name] {tool_name}")
        print(f"[tool_call_id] {request.tool_call.get('id')}")
        print("[tool_call]")
        print(textwrap.indent(short_json(request.tool_call, limit=1600), "  "))
        print("[state.before]")
        print(textwrap.indent(short_json(request.state, limit=2000), "  "))
        result = await handler(request)
        print("[tool_result]")
        print(textwrap.indent(describe_result(result), "  "))
        return result

    async def abefore_agent(self, state, runtime):
        hr(f"[{self.label}] BEFORE AGENT")
        print("[state]")
        print(textwrap.indent(short_json(state, limit=2000), "  "))
        return None

    async def aafter_agent(self, state, runtime):
        hr(f"[{self.label}] AFTER AGENT")
        print("[final_state]")
        print(textwrap.indent(short_json(state, limit=4000), "  "))
        return None


async def build_demo_agent(settings: Settings):
    model = ChatOpenAI(
        model=settings.deepseek_model,
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        temperature=0.4,
    )
    coordinator_tools = await build_coordinator_tools(settings)
    travel_tools = await build_travel_tools(settings)

    main_debug = ConsoleTraceMiddleware("main")
    travel_debug = ConsoleTraceMiddleware("travel-planner")

    subagents = [
        {
            "name": "travel-planner",
            "description": "规划旅行行程、预算、天气提醒、交通建议和装备清单。",
            "system_prompt": TRAVEL_SYSTEM_PROMPT,
            "tools": travel_tools,
            "middleware": [travel_debug],
        }
    ]

    return create_deep_agent(
        model=model,
        system_prompt=MAIN_SYSTEM_PROMPT,
        tools=coordinator_tools,
        subagents=subagents,
        middleware=[main_debug],
    )


async def main() -> None:
    settings = Settings()
    settings.validate_llm_ready()

    hr("SETTINGS")
    print(f"model: {settings.deepseek_model}")
    print(f"base_url: {settings.deepseek_base_url}")

    agent = await build_demo_agent(settings)

    hr("INPUT")
    print(TARGET_PROMPT)

    hr("RUN")
    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": TARGET_PROMPT}]},
        config={"configurable": {"thread_id": "demo-debug-travel"}},
    )

    hr("FINAL RESULT")
    print("[final_messages]")
    print(describe_messages(result["messages"]))
    print("[final_todos]")
    print(short_json(result.get("todos"), limit=4000))


if __name__ == "__main__":
    asyncio.run(main())
