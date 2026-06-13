# Thread 短期记忆实施计划

> **给执行该计划的智能体：** 必须使用 `superpowers:subagent-driven-development`（推荐）或 `superpowers:executing-plans`，按任务逐步执行。步骤使用勾选框 `- [ ]` 记录进度。

**目标：** 给当前 DeepAgent 增加基于 `thread_id` 的短期记忆，让同一个会话里的后续问题可以使用前面轮次的上下文。

**架构：** 现有 MongoDB/session 存储继续负责“会话列表、历史消息展示、刷新后 UI 恢复”。本阶段新增 LangGraph/DeepAgents checkpointer，负责“agent 推理时的 thread-scoped 短期记忆”。v1 使用进程内 checkpointer，服务重启后 checkpoint 会消失，但 Mongo transcript 仍保留。后续如果需要跨进程或重启后恢复 agent state，再单独做 Mongo/Postgres/Redis checkpointer。

**技术栈：** FastAPI、DeepAgents、LangGraph checkpointer、MongoDB session storage、SSE、pytest、Vue/Vite 回归验证。

---

## 参考资料

- 当前项目指导：`D:\AIProject\deep_agent\personalops-agent\AGENTS.md`
- 官方文档：<https://docs.langchain.com/oss/python/langgraph/persistence>
- 官方文档：<https://docs.langchain.com/oss/python/langgraph/add-memory>
- 官方文档：<https://docs.langchain.com/oss/python/langchain/short-term-memory>
- 后续计划：`D:\AIProject\deep_agent\personalops-agent\docs\plans\phase-03-backend-integration\PLANS.md`
- 只读参考项目：`D:\AIProject\deep_agent\ERP_OPENCLAW`

## 当前问题

当前项目已经有 `thread_id`，也会把消息保存进 MongoDB 或内存 session repository。但 agent 调用时只传当前这一条用户消息：

```python
async for chunk in agent.astream(
    {"messages": [{"role": "user", "content": request.message}]},
    stream_mode="messages",
):
```

这会导致一个现象：前端和 MongoDB 能看到历史消息，但 DeepAgent 本身不会在推理时自动知道上一轮说了什么。

本阶段要补的是：

```python
config={"configurable": {"thread_id": thread_id}}
```

以及：

```python
create_deep_agent(..., checkpointer=shared_checkpointer)
```

## 范围边界

- 只做同一 `thread_id` 下的短期记忆。
- 不做长期记忆，不记录跨 thread 的用户偏好。
- 不引入 DeepAgents filesystem backend。
- 不引入 skills、PPT、海报或 artifact API。
- 不改 `ERP_OPENCLAW`。
- 不把 Mongo transcript 删除或替换掉；Mongo transcript 和 LangGraph checkpoint 是两层不同能力。

## 涉及文件

- 新建：`D:\AIProject\deep_agent\personalops-agent\backend\src\personalops_agent\agent\memory.py`
- 修改：`D:\AIProject\deep_agent\personalops-agent\backend\src\personalops_agent\agent\factory.py`
- 修改：`D:\AIProject\deep_agent\personalops-agent\backend\src\personalops_agent\api\app.py`
- 修改：`D:\AIProject\deep_agent\personalops-agent\backend\tests\test_agent_factory.py`
- 修改：`D:\AIProject\deep_agent\personalops-agent\backend\tests\test_api.py`
- 必要时修改：`D:\AIProject\deep_agent\personalops-agent\frontend\tests\stream.test.js`

## 任务

### 任务 1：确认当前无短期记忆路径

- [ ] **步骤 1：阅读现有调用链**

运行：

```powershell
cd D:\AIProject\deep_agent\personalops-agent
Get-Content -Raw backend\src\personalops_agent\api\app.py
Get-Content -Raw backend\src\personalops_agent\agent\factory.py
Get-Content -Raw backend\src\personalops_agent\schemas\chat.py
```

预期确认：

- `ChatRequest` 已经有 `thread_id`。
- `stream_agent()` 已经会生成或复用 `thread_id`。
- `repo.append_message()` 已经按 `thread_id` 保存 transcript。
- `agent.astream()` 还没有传 `configurable.thread_id`。
- `create_deep_agent()` 还没有传 `checkpointer`。

- [ ] **步骤 2：保留现有 session 行为**

不要删除或弱化以下能力：

- `GET /api/sessions`
- `GET /api/sessions/{thread_id}`
- MongoDB / memory repository 的 transcript 保存
- 前端 `activeThreadId` 继续传给 `/api/chat/stream`

### 任务 2：新增 app 级共享 checkpointer

- [ ] **步骤 1：写一个会失败的 memory 模块测试**

新增或扩展测试，验证可以创建 checkpointer：

```python
from personalops_agent.agent.memory import create_short_term_checkpointer


def test_create_short_term_checkpointer_returns_reusable_instance():
    checkpointer = create_short_term_checkpointer()
    assert checkpointer is not None
```

运行：

```powershell
.\.venv\Scripts\python -m pytest backend\tests\test_agent_factory.py::test_create_short_term_checkpointer_returns_reusable_instance -q
```

预期：先失败，因为模块还没创建。

- [ ] **步骤 2：实现 `agent/memory.py`**

创建 `backend\src\personalops_agent\agent\memory.py`：

```python
from __future__ import annotations


def create_short_term_checkpointer():
    from langgraph.checkpoint.memory import InMemorySaver

    return InMemorySaver()
```

如果当前安装版本没有 `InMemorySaver`，先用本地环境确认等价类名称，例如 `MemorySaver`，并在计划执行记录里说明版本差异。

- [ ] **步骤 3：运行测试**

运行：

```powershell
.\.venv\Scripts\python -m pytest backend\tests\test_agent_factory.py -q
```

预期：通过。

### 任务 3：让 agent factory 接收 checkpointer

- [ ] **步骤 1：写 factory 失败测试**

在 `backend\tests\test_agent_factory.py` 中更新或新增测试，捕获传入 `create_deep_agent` 的参数：

```python
checkpointer = object()

agent = await factory.create_personalops_agent(
    Settings(deepseek_api_key="deepseek-secret", zhipu_api_key="zhipu-secret"),
    checkpointer=checkpointer,
)

assert agent == "agent"
assert captured["checkpointer"] is checkpointer
```

运行：

```powershell
.\.venv\Scripts\python -m pytest backend\tests\test_agent_factory.py -q
```

预期：先失败，因为 `create_personalops_agent()` 还不接受 `checkpointer`。

- [ ] **步骤 2：修改 factory 签名和调用**

把工厂函数改成：

```python
async def create_personalops_agent(settings: Settings, checkpointer=None):
```

并把参数传给 DeepAgents：

```python
return create_deep_agent(
    model=model,
    system_prompt=MAIN_SYSTEM_PROMPT,
    tools=coordinator_tools,
    subagents=subagents,
    checkpointer=checkpointer,
)
```

不要在本阶段新增 `backend=` 参数；`backend` 留给 Phase 03。

- [ ] **步骤 3：运行 factory 测试**

运行：

```powershell
.\.venv\Scripts\python -m pytest backend\tests\test_agent_factory.py -q
```

预期：通过。

### 任务 4：在 FastAPI app 中复用同一个 checkpointer

- [ ] **步骤 1：写 app 级共享测试**

在 `backend\tests\test_api.py` 中构造 fake agent factory，记录传入的 checkpointer。连续请求两次 `/api/chat/stream`，断言两次拿到同一个对象：

```python
seen_checkpointers = []

async def fake_create_agent(settings, checkpointer=None):
    seen_checkpointers.append(checkpointer)
    return fake_agent

assert seen_checkpointers[0] is seen_checkpointers[1]
```

运行：

```powershell
.\.venv\Scripts\python -m pytest backend\tests\test_api.py -q
```

预期：先失败，因为 app 还没有创建共享 checkpointer。

- [ ] **步骤 2：在 `create_app()` 中创建共享 checkpointer**

在 `backend\src\personalops_agent\api\app.py` 中：

```python
from personalops_agent.agent.memory import create_short_term_checkpointer
```

在 `create_app()` 内部、路由定义之前创建：

```python
checkpointer = create_short_term_checkpointer()
```

创建 agent 时传入：

```python
agent = await create_personalops_agent(settings, checkpointer=checkpointer)
```

注意：checkpointer 必须在 `create_app()` 级别创建一次，不要在每次请求里创建。

- [ ] **步骤 3：运行 API 测试**

运行：

```powershell
.\.venv\Scripts\python -m pytest backend\tests\test_api.py -q
```

预期：通过。

### 任务 5：给 `agent.astream()` 传入 `thread_id` config

- [ ] **步骤 1：写流式 config 测试**

在 `backend\tests\test_api.py` 中用 fake agent 捕获 `astream()` 的 `config` 参数：

```python
captured_configs = []

class FakeAgent:
    async def astream(self, payload, stream_mode=None, config=None):
        captured_configs.append(config)
        if False:
            yield None

assert captured_configs[0]["configurable"]["thread_id"] == "thread-1"
```

测试请求体传入：

```json
{"message": "第二轮问题", "thread_id": "thread-1"}
```

运行：

```powershell
.\.venv\Scripts\python -m pytest backend\tests\test_api.py -q
```

预期：先失败，因为当前还没传 `config`。

- [ ] **步骤 2：修改 `agent.astream()` 调用**

在 `backend\src\personalops_agent\api\app.py` 中改成：

```python
async for chunk in agent.astream(
    {"messages": [{"role": "user", "content": request.message}]},
    stream_mode="messages",
    config={"configurable": {"thread_id": thread_id}},
):
```

- [ ] **步骤 3：保留新会话行为**

确认没有传 `thread_id` 时，仍然生成新的 `uuid`：

```python
thread_id = request.thread_id or str(uuid.uuid4())
yield sse_event({"type": "thread", "thread_id": thread_id})
```

- [ ] **步骤 4：运行 API 测试**

运行：

```powershell
.\.venv\Scripts\python -m pytest backend\tests\test_api.py -q
```

预期：通过。

### 任务 6：完整回归验证

- [ ] **步骤 1：运行后端全量测试**

运行：

```powershell
cd D:\AIProject\deep_agent\personalops-agent
.\.venv\Scripts\python -m pytest backend\tests -q
```

预期：全部通过。

- [ ] **步骤 2：运行前端测试和构建**

运行：

```powershell
cd D:\AIProject\deep_agent\personalops-agent\frontend
npm test
npm run build
```

预期：通过。

- [ ] **步骤 3：手工浏览器验证同一 thread 的短期记忆**

启动 MongoDB、后端、前端后，在同一会话输入：

```text
我叫小李，喜欢美食和城市漫步。
```

再输入：

```text
记得我刚才说我叫什么、喜欢什么吗？
```

预期：agent 能回答“小李，喜欢美食和城市漫步”。

- [ ] **步骤 4：手工验证不同 thread 隔离**

新建会话后输入：

```text
记得我刚才说我叫什么、喜欢什么吗？
```

预期：agent 不应该继承上一个会话的记忆，应说明当前新会话里没有这些信息。

## 人工验收清单

- [ ] 同一个 `thread_id` 下，agent 能记住上一轮内容。
- [ ] 不同 `thread_id` 之间记忆隔离。
- [ ] `GET /api/sessions` 和 `GET /api/sessions/{thread_id}` 仍然正常。
- [ ] Mongo transcript 仍然保存用户和 assistant 消息。
- [ ] 服务重启后，Mongo transcript 还在，但 v1 进程内短期 checkpoint 可以消失，这个限制已在文档里说明。
- [ ] 本阶段没有引入 backend/filesystem、skills、PPT、poster 或 artifact API。

## 停止点

本阶段通过后先停下来，让你人工验证多轮对话记忆。确认之后，再进入 `phase-03-backend-integration`。
