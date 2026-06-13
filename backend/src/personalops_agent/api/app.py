from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from personalops_agent.agent.factory import create_personalops_agent
from personalops_agent.agent.memory import create_short_term_checkpointer
from personalops_agent.api.streaming import StreamCoalescer
from personalops_agent.config import Settings, get_settings
from personalops_agent.schemas.chat import ChatRequest
from personalops_agent.storage.memory import InMemorySessionRepository


def create_repository(settings: Settings):
    if settings.mongodb_uri and settings.mongodb_uri != "memory://":
        from personalops_agent.storage.mongo import MongoSessionRepository

        return MongoSessionRepository(settings.mongodb_uri, settings.mongodb_db)
    return InMemorySessionRepository()


def sse_event(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def user_facing_error(exc: Exception) -> str:
    message = str(exc)
    if "ENGINE_RESPONSE_DATA_ERROR" in message:
        return (
            "模型返回数据格式异常（ENGINE_RESPONSE_DATA_ERROR）。通常是模型在工具调用阶段"
            "返回了不符合接口要求的数据；请重试，或减少一次请求中的工具/约束复杂度。"
        )
    return message


def create_app(settings: Settings | None = None, repository=None) -> FastAPI:
    settings = settings or get_settings()
    repo = repository or create_repository(settings)
    checkpointer = create_short_term_checkpointer()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        del app
        try:
            await repo.ensure_ready()
        except Exception as exc:
            raise RuntimeError(
                "项目启动失败：MongoDB 未启动或无法连接。请先启动 MongoDB，"
                "例如运行 `docker compose up mongo`；如果只是显式本地内存调试，"
                "可将 MONGODB_URI 设置为 memory://。"
            ) from exc
        try:
            yield
        finally:
            close = getattr(repo, "close", None)
            if close:
                await close()

    app = FastAPI(title="DeepAgent PersonalOps Platform", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    async def health():
        return {
            "service": "personalops-agent",
            "status": "ok",
            "missing_travel_tool_keys": settings.missing_travel_tool_keys(),
        }

    @app.get("/api/sessions")
    async def sessions():
        records = await repo.list_sessions()
        return [record.model_dump(mode="json") for record in records]

    @app.get("/api/sessions/{thread_id}")
    async def session(thread_id: str):
        record = await repo.get_session(thread_id)
        if record:
            return record.model_dump(mode="json")
        return {"thread_id": thread_id, "messages": []}

    async def stream_agent(request: ChatRequest) -> AsyncIterator[str]:
        thread_id = request.thread_id or str(uuid.uuid4())
        yield sse_event({"type": "thread", "thread_id": thread_id})
        try:
            yield sse_event({"type": "status", "message": "正在保存本轮会话..."})
            await repo.append_message(thread_id, "user", request.message)
            yield sse_event({"type": "status", "message": "正在创建 Agent 并准备工具..."})
            agent = await create_personalops_agent(settings, checkpointer=checkpointer)
            coalescer = StreamCoalescer()
            collected = ""
            yield sse_event({"type": "status", "message": "Agent 正在分析你的需求..."})
            async for chunk in agent.astream(
                {"messages": [{"role": "user", "content": request.message}]},
                stream_mode="messages",
                config={"configurable": {"thread_id": thread_id}},
            ):
                token = chunk[0] if isinstance(chunk, tuple) else chunk
                tool_chunks = getattr(token, "tool_call_chunks", None)
                if tool_chunks:
                    for tool_chunk in tool_chunks:
                        if tool_chunk.get("name"):
                            for event in coalescer.start_tool(
                                tool_chunk["name"],
                                tool_call_id=tool_chunk.get("id"),
                            ):
                                yield sse_event(event)
                        if tool_chunk.get("args"):
                            for event in coalescer.add_tool_args(
                                tool_chunk["args"],
                                tool_call_id=tool_chunk.get("id"),
                            ):
                                yield sse_event(event)
                    continue

                if getattr(token, "type", None) == "tool":
                    for event in coalescer.finish_tool(
                        getattr(token, "name", "unknown"),
                        getattr(token, "content", ""),
                        tool_call_id=getattr(token, "tool_call_id", None),
                    ):
                        yield sse_event(event)
                    continue

                content = getattr(token, "content", "")
                if isinstance(content, str) and content:
                    collected += content
                    for event in coalescer.add_text(content):
                        yield sse_event(event)

            for event in coalescer.flush_text():
                yield sse_event(event)
            await repo.append_message(thread_id, "assistant", collected)
            yield sse_event({"type": "done", "thread_id": thread_id, "content": collected})
        except Exception as exc:
            message = user_facing_error(exc)
            try:
                await repo.append_message(thread_id, "assistant", f"运行失败：{message}")
            except Exception:
                pass
            yield sse_event({"type": "error", "message": message, "thread_id": thread_id})

    @app.post("/api/chat/stream")
    async def chat_stream(request: ChatRequest):
        return StreamingResponse(stream_agent(request), media_type="text/event-stream")

    return app


app = create_app()
