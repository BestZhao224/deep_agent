# Artifact API 与前端展示实施计划

> **给执行该计划的智能体：** 必须使用 `superpowers:subagent-driven-development`（推荐）或 `superpowers:executing-plans`，按任务逐步执行。步骤使用勾选框 `- [ ]` 记录进度。

**目标：** 增加 artifact 存储、artifact API、SSE artifact 事件和前端 artifact 卡片，让用户可以在聊天界面里下载生成好的 PPT。

**架构：** 这一阶段把 Phase 04 的本地 PPT 生成器变成用户可见的 artifact 流。后端负责创建 artifact 元数据并把文件存到本地受控目录；聊天流负责发出结构化 artifact 事件；Vue 前端在对应的 assistant 回复下面渲染卡片。本阶段只接 PPT artifact，poster artifact 放到 Phase 06。

**技术栈：** FastAPI、StreamingResponse/SSE、Pydantic、本地文件系统 artifact 存储、Vue、Vite、Vitest、pytest。

---

## 参考资料

- 依赖上一个计划：`D:\AIProject\deep_agent\personalops-agent\docs\plans\phase-04-skills-ppt-generator\PLANS.md`
- 官方文档：<https://docs.langchain.com/oss/python/deepagents/backends>
- 官方文档：<https://docs.langchain.com/oss/python/deepagents/skills>
- 当前前端流式相关文件：`frontend\src\lib\stream.js`、`frontend\src\App.vue`、`frontend\src\styles.css`
- 只读参考项目：`D:\AIProject\deep_agent\ERP_OPENCLAW`

## 范围边界

- 不新增 poster 生成。
- 不把 artifact 迁移到 sandbox。
- 不重做整个聊天 UI。
- 不把本地文件系统路径直接展示给用户。

## 涉及文件

- 新建：`D:\AIProject\deep_agent\personalops-agent\backend\src\personalops_agent\artifacts\models.py`
- 新建：`D:\AIProject\deep_agent\personalops-agent\backend\src\personalops_agent\artifacts\store.py`
- 新建：`D:\AIProject\deep_agent\personalops-agent\backend\tests\test_artifacts.py`
- 修改：`D:\AIProject\deep_agent\personalops-agent\backend\src\personalops_agent\api\app.py`
- 修改：`D:\AIProject\deep_agent\personalops-agent\backend\src\personalops_agent\api\streaming.py`
- 修改：`D:\AIProject\deep_agent\personalops-agent\frontend\src\lib\stream.js`
- 修改：`D:\AIProject\deep_agent\personalops-agent\frontend\src\App.vue`
- 修改：`D:\AIProject\deep_agent\personalops-agent\frontend\src\styles.css`
- 修改或新建：`D:\AIProject\deep_agent\personalops-agent\frontend\tests\stream.test.js`

## 任务

### 任务 1：增加 artifact 元数据和本地存储

- [ ] **步骤 1：写一个会失败的存储测试**

创建 `backend\tests\test_artifacts.py`：

```python
from personalops_agent.artifacts.models import ArtifactKind
from personalops_agent.artifacts.store import LocalArtifactStore


def test_local_artifact_store_registers_and_reads_file(tmp_path):
    source = tmp_path / "source.pptx"
    source.write_bytes(b"pptx-bytes")
    store = LocalArtifactStore(tmp_path / "artifacts")

    artifact = store.save_file(
        session_id="session-1",
        message_id="message-1",
        kind=ArtifactKind.PPTX,
        source_path=source,
        filename="tokyo-plan.pptx",
    )

    assert artifact.kind == ArtifactKind.PPTX
    assert artifact.filename == "tokyo-plan.pptx"
    assert artifact.download_url == f"/api/artifacts/{artifact.id}"
    assert store.resolve_path(artifact.id).read_bytes() == b"pptx-bytes"
```

运行：

```powershell
.\.venv\Scripts\python -m pytest backend\tests\test_artifacts.py -q
```

预期：先失败，因为 artifact 模块还不存在。

- [ ] **步骤 2：实现模型和本地存储**

创建如下结构：

```python
class ArtifactKind(str, Enum):
    PPTX = "pptx"


class ArtifactStatus(str, Enum):
    READY = "ready"
    FAILED = "failed"


class ArtifactRecord(BaseModel):
    id: str
    session_id: str
    message_id: str
    kind: ArtifactKind
    filename: str
    content_type: str
    status: ArtifactStatus
    download_url: str
    error: str | None = None
```

`LocalArtifactStore` 需要做到：

- 使用可配置的根目录。
- 把文件复制到 `root/session_id/artifact_id-filename`。
- 在当前进程内维护元数据。
- 可以通过 artifact id 找回文件路径。

- [ ] **步骤 3：运行存储测试**

运行：

```powershell
.\.venv\Scripts\python -m pytest backend\tests\test_artifacts.py -q
```

预期：通过。

### 任务 2：增加下载 API

- [ ] **步骤 1：写一个会失败的 API 测试**

在 `backend\tests\test_api.py` 里加一个测试，先在 app 的 store 里注册 artifact，再调用：

```http
GET /api/artifacts/{artifact_id}
```

预期响应：

- HTTP 200
- PPTX 对应的 content type 正确
- 返回字节和存储内容一致

- [ ] **步骤 2：实现路由**

在 `backend\src\personalops_agent\api\app.py` 中增加：

```python
@app.get("/api/artifacts/{artifact_id}")
async def download_artifact(artifact_id: str):
    ...
```

使用 `FileResponse`，未知 artifact id 返回 404。

- [ ] **步骤 3：运行 API 测试**

运行：

```powershell
.\.venv\Scripts\python -m pytest backend\tests\test_api.py backend\tests\test_artifacts.py -q
```

预期：通过。

### 任务 3：增加 SSE artifact 事件结构

- [ ] **步骤 1：增加流式测试**

在 `backend\tests\test_streaming.py` 中加入 `artifact` 事件测试：

```python
event = coalescer.artifact(record)
assert '"type":"artifact"' in event
assert '"download_url":"/api/artifacts/' in event
```

- [ ] **步骤 2：实现事件帮助函数**

在 `backend\src\personalops_agent\api\streaming.py` 中增加一个方法，输出结构化 JSON：

```json
{
  "type": "artifact",
  "artifact": {
    "id": "...",
    "kind": "pptx",
    "filename": "...",
    "status": "ready",
    "download_url": "/api/artifacts/..."
  }
}
```

- [ ] **步骤 3：运行流式测试**

运行：

```powershell
.\.venv\Scripts\python -m pytest backend\tests\test_streaming.py -q
```

预期：通过。

### 任务 4：在前端渲染 artifact 卡片

- [ ] **步骤 1：写前端流测试**

在 `frontend\tests\stream.test.js` 中加入一个测试，喂入 artifact 事件后，断言当前 assistant turn 有 artifact：

```javascript
expect(state.messages.at(-1).artifacts[0]).toMatchObject({
  kind: 'pptx',
  filename: 'tokyo-plan.pptx',
  status: 'ready',
})
```

运行：

```powershell
cd D:\AIProject\deep_agent\personalops-agent\frontend
npm test
```

预期：在流处理还没实现时先失败。

- [ ] **步骤 2：更新流状态模型**

在 `frontend\src\lib\stream.js` 中：

- 给 assistant message 加 `artifacts: []`。
- 处理 `type === "artifact"`。
- 把 artifact 挂到当前 assistant 回复下，不要单独做全局区块。

- [ ] **步骤 3：增加卡片 UI**

在 `frontend\src\App.vue` 中：

- 在 assistant message 下渲染 artifact 卡片。
- 显示文件名、类型、状态和下载链接。
- `href` 指向 `artifact.download_url`。

在 `frontend\src\styles.css` 中：

- 补充紧凑的卡片样式，和当前聊天 UI 保持一致。
- 保证移动端布局稳定。

- [ ] **步骤 4：运行前端检查**

运行：

```powershell
cd D:\AIProject\deep_agent\personalops-agent\frontend
npm test
npm run build
```

预期：通过。

## 验证

运行完整测试：

```powershell
cd D:\AIProject\deep_agent\personalops-agent
.\.venv\Scripts\python -m pytest backend\tests -q
cd frontend
npm test
npm run build
```

手工浏览器验证：

1. 启动 MongoDB、后端和前端。
2. 先让系统生成一份旅行规划。
3. 再输入：`把刚才的旅行规划生成 PPT。`
4. 确认页面里出现 PPT artifact 卡片。
5. 点击下载。
6. 打开 `.pptx`。

## 人工验收清单

- [ ] PPT artifact 卡片出现在对应 assistant 回复下。
- [ ] 下载链接能返回真实 `.pptx`。
- [ ] 缺少 artifact id 时返回 404。
- [ ] PPT 生成出错时，前端能显示可读错误。
- [ ] 原有旅行规划和工具过程展示不回退。
- [ ] 本阶段不出现 poster generator。

## 停止点

本阶段通过后先停下来，让你检查完整的 PPT artifact 流程。确认后再进入 Phase 06。
