from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient

from personalops_agent.schemas.chat import ChatMessage, SessionRecord


class MongoSessionRepository:
    """MongoDB-backed session repository."""

    def __init__(self, uri: str, db_name: str):
        self.client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=3000)
        self.db = self.client[db_name]
        self.sessions = self.db["sessions"]

    async def ensure_ready(self) -> None:
        await self.client.admin.command("ping")

    async def append_message(self, thread_id: str, role: str, content: str) -> None:
        now = datetime.now(UTC)
        message = ChatMessage(role=role, content=content, created_at=now).model_dump(mode="json")
        update: dict[str, Any] = {
            "$setOnInsert": {
                "thread_id": thread_id,
                "title": content[:40] if role == "user" else "新会话",
                "created_at": now,
            },
            "$set": {"updated_at": now},
            "$push": {"messages": message},
        }
        await self.sessions.update_one({"thread_id": thread_id}, update, upsert=True)

    async def get_session(self, thread_id: str) -> SessionRecord | None:
        document = await self.sessions.find_one({"thread_id": thread_id}, {"_id": 0})
        return SessionRecord.model_validate(document) if document else None

    async def list_sessions(self) -> list[SessionRecord]:
        cursor = self.sessions.find({}, {"_id": 0}).sort("updated_at", -1).limit(50)
        return [SessionRecord.model_validate(document) async for document in cursor]

    async def close(self) -> None:
        self.client.close()
