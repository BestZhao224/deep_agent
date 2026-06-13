import pytest

from personalops_agent.storage.memory import InMemorySessionRepository


@pytest.mark.asyncio
async def test_session_repository_appends_and_lists_messages():
    repo = InMemorySessionRepository()

    await repo.append_message("thread-1", "user", "hello")
    await repo.append_message("thread-1", "assistant", "hi")

    session = await repo.get_session("thread-1")
    sessions = await repo.list_sessions()

    assert session is not None
    assert [message.role for message in session.messages] == ["user", "assistant"]
    assert sessions[0].thread_id == "thread-1"
