import pytest
from fastapi.testclient import TestClient

from personalops_agent.api import app as app_module
from personalops_agent.api.app import create_app, create_repository, user_facing_error
from personalops_agent.config import Settings
from personalops_agent.storage.memory import InMemorySessionRepository


def test_health_endpoint_reports_service_name():
    client = TestClient(create_app())

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["service"] == "personalops-agent"


def test_memory_uri_selects_in_memory_repository():
    repo = create_repository(Settings(mongodb_uri="memory://"))

    assert isinstance(repo, InMemorySessionRepository)


def test_app_startup_fails_fast_when_mongodb_is_unavailable():
    class UnavailableMongoRepository:
        async def ensure_ready(self):
            raise RuntimeError("connection refused")

        async def append_message(self, thread_id, role, content):
            raise AssertionError("should not handle requests before startup succeeds")

        async def list_sessions(self):
            return []

        async def get_session(self, thread_id):
            return None

    with pytest.raises(RuntimeError, match="MongoDB 未启动或无法连接"):
        with TestClient(
            create_app(
                Settings(mongodb_uri="mongodb://localhost:27017"),
                repository=UnavailableMongoRepository(),
            )
        ):
            pass


def test_chat_stream_returns_error_event_when_storage_fails_before_agent_start():
    class FailingRepository:
        async def append_message(self, thread_id, role, content):
            raise RuntimeError("storage unavailable")

        async def list_sessions(self):
            return []

        async def get_session(self, thread_id):
            return None

    client = TestClient(create_app(Settings(), repository=FailingRepository()))

    response = client.post("/api/chat/stream", json={"message": "hello"})

    assert response.status_code == 200
    assert '"type": "error"' in response.text
    assert "storage unavailable" in response.text


def test_chat_stream_emits_status_before_slow_agent_work():
    class FailingRepository:
        async def ensure_ready(self):
            return None

        async def append_message(self, thread_id, role, content):
            raise RuntimeError("storage unavailable")

        async def list_sessions(self):
            return []

        async def get_session(self, thread_id):
            return None

    client = TestClient(create_app(Settings(), repository=FailingRepository()))

    response = client.post("/api/chat/stream", json={"message": "hello"})

    assert '"type": "thread"' in response.text
    assert '"type": "status"' in response.text
    assert response.text.index('"type": "status"') < response.text.index('"type": "error"')


def test_chat_stream_reuses_app_level_checkpointer(monkeypatch):
    seen_checkpointers = []

    class Repository:
        async def ensure_ready(self):
            return None

        async def append_message(self, thread_id, role, content):
            return None

        async def list_sessions(self):
            return []

        async def get_session(self, thread_id):
            return None

    class FakeAgent:
        async def astream(self, payload, stream_mode=None, config=None):
            if False:
                yield None

    async def fake_create_agent(settings, checkpointer=None):
        seen_checkpointers.append(checkpointer)
        return FakeAgent()

    monkeypatch.setattr(app_module, "create_personalops_agent", fake_create_agent)

    client = TestClient(create_app(Settings(), repository=Repository()))

    first = client.post("/api/chat/stream", json={"message": "hello", "thread_id": "thread-1"})
    second = client.post("/api/chat/stream", json={"message": "again", "thread_id": "thread-1"})

    assert first.status_code == 200
    assert second.status_code == 200
    assert seen_checkpointers[0] is not None
    assert seen_checkpointers[0] is seen_checkpointers[1]


def test_chat_stream_passes_thread_id_to_agent_config(monkeypatch):
    captured_configs = []

    class Repository:
        async def ensure_ready(self):
            return None

        async def append_message(self, thread_id, role, content):
            return None

        async def list_sessions(self):
            return []

        async def get_session(self, thread_id):
            return None

    class FakeAgent:
        async def astream(self, payload, stream_mode=None, config=None):
            captured_configs.append(config)
            if False:
                yield None

    async def fake_create_agent(settings, checkpointer=None):
        return FakeAgent()

    monkeypatch.setattr(app_module, "create_personalops_agent", fake_create_agent)

    client = TestClient(create_app(Settings(), repository=Repository()))

    response = client.post(
        "/api/chat/stream",
        json={"message": "second turn", "thread_id": "thread-1"},
    )

    assert response.status_code == 200
    assert captured_configs[0]["configurable"]["thread_id"] == "thread-1"


def test_chat_stream_without_thread_id_still_emits_generated_thread(monkeypatch):
    class Repository:
        async def ensure_ready(self):
            return None

        async def append_message(self, thread_id, role, content):
            return None

        async def list_sessions(self):
            return []

        async def get_session(self, thread_id):
            return None

    class FakeAgent:
        async def astream(self, payload, stream_mode=None, config=None):
            if False:
                yield None

    async def fake_create_agent(settings, checkpointer=None):
        return FakeAgent()

    monkeypatch.setattr(app_module, "create_personalops_agent", fake_create_agent)

    client = TestClient(create_app(Settings(), repository=Repository()))

    response = client.post("/api/chat/stream", json={"message": "new thread"})

    assert response.status_code == 200
    assert '"type": "thread"' in response.text
    assert '"thread_id":' in response.text


def test_engine_response_data_error_is_mapped_to_user_facing_message():
    message = user_facing_error(RuntimeError("API 调用失败：ENGINE_RESPONSE_DATA_ERROR"))

    assert "模型返回数据格式异常" in message
    assert "ENGINE_RESPONSE_DATA_ERROR" in message
