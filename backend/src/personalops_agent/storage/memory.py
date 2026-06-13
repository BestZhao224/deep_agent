from __future__ import annotations

from datetime import UTC, datetime

from personalops_agent.schemas.chat import ChatMessage, SessionRecord


class InMemorySessionRepository:
    """Development/test repository with the same API shape as Mongo storage."""

    def __init__(self):
        self._sessions: dict[str, SessionRecord] = {}

    async def ensure_ready(self) -> None:
        return None

    async def append_message(self, thread_id: str, role: str, content: str) -> None:
        now = datetime.now(UTC)
        session = self._sessions.get(thread_id)
        if session is None:
            session = SessionRecord(thread_id=thread_id, created_at=now, updated_at=now)
            self._sessions[thread_id] = session
        session.messages.append(ChatMessage(role=role, content=content, created_at=now))
        session.updated_at = now
        if role == "user" and session.title == "新会话":
            session.title = content[:40]

    async def get_session(self, thread_id: str) -> SessionRecord | None:
        return self._sessions.get(thread_id)

    async def list_sessions(self) -> list[SessionRecord]:
        return sorted(self._sessions.values(), key=lambda item: item.updated_at, reverse=True)
