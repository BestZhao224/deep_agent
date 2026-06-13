from __future__ import annotations

from dataclasses import dataclass

TOOL_DISPLAY_NAMES = {
    "write_todos": "规划任务",
    "search_web": "联网搜索",
    "get_weather": "天气查询",
    "convert_currency": "汇率换算",
}


def display_tool_name(tool_name: str) -> str:
    return TOOL_DISPLAY_NAMES.get(tool_name, tool_name)


def compact_text(value: object, limit: int = 500) -> str:
    text = value if isinstance(value, str) else str(value)
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return f"{text[:limit]}..."


def compact_tool_result(tool_name: str, result: object) -> str:
    text = result if isinstance(result, str) else str(result)
    if tool_name == "write_todos" and text.startswith("Updated todo list"):
        return "任务列表已更新"
    return compact_text(text, limit=240)


@dataclass
class ActiveToolCall:
    name: str
    tool_call_id: str | None = None
    args: str = ""


class StreamCoalescer:
    """Coalesce low-level model stream chunks into UI-friendly SSE events."""

    def __init__(self, text_flush_chars: int = 80):
        self.text_flush_chars = text_flush_chars
        self._text_buffer = ""
        self._tool_stack: list[ActiveToolCall] = []

    def add_text(self, content: str) -> list[dict]:
        self._text_buffer += content
        if self._should_flush_text():
            return self.flush_text()
        return []

    def flush_text(self) -> list[dict]:
        if not self._text_buffer:
            return []
        content = self._text_buffer
        self._text_buffer = ""
        return [{"type": "token", "content": content}]

    def start_tool(self, tool_name: str, tool_call_id: str | None = None) -> list[dict]:
        self._tool_stack.append(ActiveToolCall(name=tool_name, tool_call_id=tool_call_id))
        return [
            {
                "type": "tool_start",
                "phase": "started",
                "tool_call_id": tool_call_id,
                "tool_name": tool_name,
                "display_name": display_tool_name(tool_name),
                "status": "running",
            }
        ]

    def add_tool_args(self, args: str, tool_call_id: str | None = None) -> list[dict]:
        active = self._find_tool_call(tool_call_id) if tool_call_id else None
        if active is None and self._tool_stack:
            active = self._tool_stack[-1]
        if active:
            active.args += args
        resolved_name = active.name if active else "unknown"
        resolved_call_id = tool_call_id or (active.tool_call_id if active else None)
        return [
            {
                "type": "tool_args",
                "phase": "args",
                "tool_call_id": resolved_call_id,
                "tool_name": resolved_name,
                "display_name": display_tool_name(resolved_name),
                "status": "running",
                "args_delta": args,
            }
        ]

    def finish_tool(self, tool_name: str, result: object, tool_call_id: str | None = None) -> list[dict]:
        active = self._pop_tool_call(tool_call_id) if tool_call_id else None
        if active is None:
            active = self._tool_stack.pop() if self._tool_stack else ActiveToolCall(name=tool_name)
        resolved_name = active.name or tool_name
        resolved_call_id = tool_call_id or active.tool_call_id
        return [
            {
                "type": "tool_result",
                "phase": "completed",
                "tool_call_id": resolved_call_id,
                "tool_name": resolved_name,
                "display_name": display_tool_name(resolved_name),
                "status": "done",
                "result": compact_tool_result(resolved_name, result),
            }
        ]

    def _should_flush_text(self) -> bool:
        if len(self._text_buffer) >= self.text_flush_chars:
            return True
        return self._text_buffer.endswith((".", "!", "?", "。", "！", "？", "\n"))

    def _find_tool_call(self, tool_call_id: str | None) -> ActiveToolCall | None:
        if not tool_call_id:
            return None
        return next(
            (tool_call for tool_call in self._tool_stack if tool_call.tool_call_id == tool_call_id),
            None,
        )

    def _pop_tool_call(self, tool_call_id: str | None) -> ActiveToolCall | None:
        if not tool_call_id:
            return None
        for index, tool_call in enumerate(self._tool_stack):
            if tool_call.tool_call_id == tool_call_id:
                return self._tool_stack.pop(index)
        return None
