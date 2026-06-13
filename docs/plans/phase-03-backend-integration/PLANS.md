# DeepAgents 后端接入实施计划

> **给执行该计划的智能体：** 必须使用 `superpowers:subagent-driven-development`（推荐）或 `superpowers:executing-plans`，按任务逐步执行。步骤使用勾选框 `- [ ]` 记录进度。

**目标：** 显式接入 DeepAgents backend，同时保持当前的旅行规划、工具、MCP、SSE、MongoDB 会话和 Vue 聊天界面全部可用。

**架构：** 这一阶段只给现有 agent 工厂增加 DeepAgents backend 层。建议使用以项目 `backend` 目录为根的 `FilesystemBackend`，这样后续 Phase 04 可以直接从 `/skills/...` 读取项目内 skills，而不必再换 backend 类型。主 agent 仍然只负责协调，只保留 `search_web`；`travel-planner` 仍然是唯一的旅行专家，继续拥有天气、汇率、搜索和 AMap MCP 工具。本阶段不引入 PPT、海报、artifact API，也不改前端 artifact 体验。

**技术栈：** FastAPI、LangChain、DeepAgents、DeepAgents backends、DeepSeek 兼容的 ChatOpenAI、MongoDB、Vue/Vite、Vitest、pytest。

---

## 参考资料

- 项目总指导：`D:\AIProject\deep_agent\personalops-agent\AGENTS.md`
- 官方文档：<https://docs.langchain.com/oss/python/deepagents/backends>
- 官方文档：<https://docs.langchain.com/oss/python/deepagents/subagents>
- 官方文档：<https://docs.langchain.com/oss/python/deepagents/customization>
- 只读参考项目：`D:\AIProject\deep_agent\ERP_OPENCLAW`

## 范围边界

- 不新增 PPT 生成。
- 不新增海报生成。
- 不新增 artifact API 或下载接口。
- 不改前端 UI，除非后端接入引发了极小的兼容修复。
- 不修改 `ERP_OPENCLAW`。

## 涉及文件

- 修改：`D:\AIProject\deep_agent\personalops-agent\backend\src\personalops_agent\agent\factory.py`
- 修改：`D:\AIProject\deep_agent\personalops-agent\backend\tests\test_agent_factory.py`
- 新建：`D:\AIProject\deep_agent\personalops-agent\backend\src\personalops_agent\agent\backend.py`
- 新建：`D:\AIProject\deep_agent\personalops-agent\backend\tests\test_agent_backend.py`

## 任务

### 任务 1：锁定当前 agent 边界

- [ ] **步骤 1：阅读当前工厂和测试**

运行：

```powershell
cd D:\AIProject\deep_agent\personalops-agent
Get-Content -Raw backend\src\personalops_agent\agent\factory.py
Get-Content -Raw backend\tests\test_agent_factory.py
```

预期：当前 `create_personalops_agent()` 传入 `tools=coordinator_tools`，并且只有一个 `travel-planner` subagent，且该 subagent 只拿旅行相关工具。

- [ ] **步骤 2：补或更新工具边界回归测试**

在 `backend\tests\test_agent_factory.py` 中保留或新增如下断言：

```python
assert captured["tools"] == ["coordinator-search"]
assert captured["subagents"][0]["name"] == "travel-planner"
assert captured["subagents"][0]["tools"] == ["travel-search", "weather", "exchange", "amap"]
```

- [ ] **步骤 3：运行针对性测试**

运行：

```powershell
.\.venv\Scripts\python -m pytest backend\tests\test_agent_factory.py -q
```

预期：在接入 backend 之前测试先通过。如果失败，先修复现有回归，再继续。

### 任务 2：增加显式 DeepAgents backend 工厂

- [ ] **步骤 1：写一个会失败的 backend 测试**

在 `backend\tests\test_agent_factory.py` 中新增一个测试，捕获传入 `create_deep_agent` 的 kwargs，并断言存在 `backend`：

```python
assert "backend" in captured
assert captured["backend"] is not None
```

运行：

```powershell
.\.venv\Scripts\python -m pytest backend\tests\test_agent_factory.py::test_create_agent_passes_explicit_backend -q
```

预期：先失败，因为当前还没有显式传入 backend。

- [ ] **步骤 2：实现最小 backend 创建器**

按照官方 DeepAgents backend 文档，在 `backend\src\personalops_agent\agent\backend.py` 中实现一个小助手：

```python
from pathlib import Path


def get_project_backend_root() -> Path:
    return Path(__file__).resolve().parents[3]


def create_project_backend():
    from deepagents.backends.filesystem import FilesystemBackend

    return FilesystemBackend(root_dir=str(get_project_backend_root()))
```

然后在工厂中传入：

```python
return create_deep_agent(
    model=model,
    system_prompt=MAIN_SYSTEM_PROMPT,
    tools=coordinator_tools,
    subagents=subagents,
    backend=backend,
)
```

把 import 放在 `create_personalops_agent()` 内部，保证测试时可以 monkeypatch DeepAgents 模块。

- [ ] **步骤 3：运行聚焦测试**

运行：

```powershell
.\.venv\Scripts\python -m pytest backend\tests\test_agent_factory.py -q
```

预期：factory 相关测试全部通过。

### 任务 3：确认 backend 不破坏 API 流式输出

- [ ] **步骤 1：跑后端测试套件**

运行：

```powershell
.\.venv\Scripts\python -m pytest backend\tests -q
```

预期：全部通过。

- [ ] **步骤 2：跑前端测试和构建**

运行：

```powershell
cd D:\AIProject\deep_agent\personalops-agent\frontend
npm test
npm run build
```

预期：Vitest 和 Vite 构建通过。

- [ ] **步骤 3：做一次手工 SSE 冒烟测试**

如果使用真实 Mongo，先启动：

```powershell
cd D:\AIProject\deep_agent\personalops-agent
docker compose up mongo
```

启动后端：

```powershell
cd D:\AIProject\deep_agent\personalops-agent\backend
uvicorn personalops_agent.main:app --reload --host 0.0.0.0 --port 8000
```

启动前端：

```powershell
cd D:\AIProject\deep_agent\personalops-agent\frontend
npm run dev
```

在浏览器中输入：

```text
帮我规划一个东京 5 天旅行，预算 8000 人民币，偏美食和城市漫步。
```

预期：聊天正常流式返回，工具过程仍然挂在对应用户消息下，不会出现大段 raw JSON 冲屏。

## 人工验收清单

- [ ] 当前旅行规划仍然正常。
- [ ] 主 agent 仍然只保留 `search_web`。
- [ ] `travel-planner` 仍然独占天气、汇率、搜索和 AMap MCP 工具。
- [ ] `create_deep_agent` 收到的是以 `D:\AIProject\deep_agent\personalops-agent\backend` 为根的 `FilesystemBackend`。
- [ ] SSE 仍然能快速发出状态。
- [ ] 前端仍然能把工具过程折叠显示在对应用户消息下。
- [ ] 本阶段不出现 PPT、海报、artifact API 或 artifact UI。

## 停止点

本阶段通过后先停下来，让你测试“接入 backend 后的旅行规划”。在你确认前，不进入 Phase 04。
