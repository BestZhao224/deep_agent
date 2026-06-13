# Poster 生成 subagent 实施计划

> **给执行该计划的智能体：** 必须使用 `superpowers:subagent-driven-development`（推荐）或 `superpowers:executing-plans`，按任务逐步执行。步骤使用勾选框 `- [ ]` 记录进度。

**目标：** 在已经跑通的 backend、skills、artifact API 和前端 artifact UI 基础上，只新增 `poster-generator` subagent。

**架构：** 这一阶段是 artifact 流的增量扩展。`poster-generator` 和 `travel-planner`、`ppt-generator` 处于平行关系，消费同一份旅行计划或旅行 brief，生成竖版 HTML 海报，再渲染成 `poster.png` 并登记为 artifact。因为自定义 DeepAgents subagent 不会自动继承主 agent skills，所以 `poster-generator` 必须显式配置 `skills=["/skills/travel-poster/"]`。现有 artifact API 和前端卡片直接复用。

**技术栈：** DeepAgents subagents、项目内 skills、本地 artifact backend、HTML/CSS 海报渲染、Playwright 或等价浏览器渲染器、FastAPI、Vue/Vite、pytest、Vitest。

---

## 参考资料

- 依赖上一个计划：`D:\AIProject\deep_agent\personalops-agent\docs\plans\phase-05-artifact-api-ux\PLANS.md`
- 官方文档：<https://docs.langchain.com/oss/python/deepagents/skills>
- 官方文档：<https://docs.langchain.com/oss/python/deepagents/subagents>
- 官方文档：<https://docs.langchain.com/oss/python/deepagents/backends>
- 用户提供的视觉参考：密集型竖版中文信息图 / 流程海报风格
- 可选参考：本地 `imagegen` skill 的 `infographic-diagram` 提示结构，但 v1 优先使用确定性的 HTML/CSS 方案
- 只读参考项目：`D:\AIProject\deep_agent\ERP_OPENCLAW`

## 范围边界

- 不重写 PPT 流程。
- 不把 backend 换成 sandbox。
- v1 不依赖图像模型来保证中文文字准确。
- 不在 assistant 文本里暴露原始 HTML 路径。

## 涉及文件

- 新建：`D:\AIProject\deep_agent\personalops-agent\backend\skills\travel-poster\SKILL.md`
- 新建：`D:\AIProject\deep_agent\personalops-agent\backend\src\personalops_agent\artifacts\poster.py`
- 新建：`D:\AIProject\deep_agent\personalops-agent\backend\tests\test_poster_generator.py`
- 修改：`D:\AIProject\deep_agent\personalops-agent\backend\src\personalops_agent\artifacts\models.py`
- 修改：`D:\AIProject\deep_agent\personalops-agent\backend\src\personalops_agent\agent\prompts.py`
- 修改：`D:\AIProject\deep_agent\personalops-agent\backend\src\personalops_agent\agent\factory.py`
- 修改：`D:\AIProject\deep_agent\personalops-agent\backend\tests\test_agent_factory.py`
- 必要时修改：`D:\AIProject\deep_agent\personalops-agent\frontend\src\App.vue`
- 必要时修改：`D:\AIProject\deep_agent\personalops-agent\frontend\src\lib\stream.js`

## 任务

### 任务 1：为 poster 扩展 artifact 类型

- [ ] **步骤 1：写一个会失败的 artifact 类型测试**

在 `backend\tests\test_artifacts.py` 中新增：

```python
from personalops_agent.artifacts.models import ArtifactKind


def test_artifact_kind_supports_poster_png():
    assert ArtifactKind.POSTER_PNG == "poster_png"
```

运行：

```powershell
.\.venv\Scripts\python -m pytest backend\tests\test_artifacts.py -q
```

预期：先失败，因为 `POSTER_PNG` 还不存在。

- [ ] **步骤 2：增加 poster 类型和 content type 映射**

在 `backend\src\personalops_agent\artifacts\models.py` 中加入：

```python
POSTER_PNG = "poster_png"
```

并确保 store 能把 `poster_png` 映射到 `image/png`。

- [ ] **步骤 3：运行 artifact 测试**

运行：

```powershell
.\.venv\Scripts\python -m pytest backend\tests\test_artifacts.py -q
```

预期：通过。

### 任务 2：增加 Travel Poster skill

- [ ] **步骤 1：创建 skill 文件**

创建 `backend\skills\travel-poster\SKILL.md`：

```markdown
---
name: travel-poster
description: 根据结构化的旅行 brief 生成竖版中文旅行信息图海报。
---

# Travel Poster Skill

当用户要把旅行计划做成海报、长图、信息图、路线海报或可分享总结图时，使用这个 skill。

## 输出

生成一张竖版海报，包含清晰的中文文字和分层内容：

1. 标题与旅行总览
2. 路线或按天流程
3. 预算拆分
4. 美食与城市漫步亮点
5. 交通与天气提醒
6. 最终检查清单

## 风格

- 信息密度要高，但层次必须清楚。
- 使用分区、编号、图标、箭头和紧凑卡片。
- 保留旅行计划里的事实信息。
- 不要编造地点、价格、天气或来源。
- 文字清晰度比装饰性更重要。
```

- [ ] **步骤 2：补 skill 存在性测试**

在 `backend\tests\test_agent_factory.py` 中加入：

```python
from pathlib import Path


def test_travel_poster_skill_exists():
    skill = Path("backend/skills/travel-poster/SKILL.md")
    assert skill.exists()
    text = skill.read_text(encoding="utf-8")
    assert "travel-poster" in text
    assert "竖版" in text
```

运行：

```powershell
.\.venv\Scripts\python -m pytest backend\tests\test_agent_factory.py::test_travel_poster_skill_exists -q
```

预期：skill 文件存在后通过。

### 任务 3：添加确定性的海报生成器

- [ ] **步骤 1：写一个会失败的海报生成测试**

创建 `backend\tests\test_poster_generator.py`：

```python
from personalops_agent.artifacts.poster import TravelPosterBrief, create_travel_poster_html


def test_create_travel_poster_html_contains_core_sections(tmp_path):
    brief = TravelPosterBrief(
        title="东京 5 天美食城市漫步",
        destination="东京",
        duration_days=5,
        budget="8000 人民币",
        daily_plan=["Day 1: 浅草", "Day 2: 上野"],
        budget_notes=["住宿 3000", "餐饮 2200"],
        highlights=["拉面", "咖啡馆", "城市漫步"],
        reminders=["提前确认天气"],
    )

    output = create_travel_poster_html(brief, tmp_path / "poster.html")

    text = output.read_text(encoding="utf-8")
    assert "东京 5 天美食城市漫步" in text
    assert "预算" in text
    assert "每日行程" in text
```

运行：

```powershell
.\.venv\Scripts\python -m pytest backend\tests\test_poster_generator.py -q
```

预期：先失败，因为模块还没实现。

- [ ] **步骤 2：实现 HTML 生成器**

创建 `backend\src\personalops_agent\artifacts\poster.py`：

- 定义 `TravelPosterBrief`。
- 实现 `create_travel_poster_html(brief, output_path)`。
- 输出一个带内嵌 CSS 的独立 HTML 文件。
- 画布建议使用约 `1080px` 宽的竖版布局。
- 让中文文字清楚、分区明显。

- [ ] **步骤 3：增加 PNG 渲染**

实现 `render_travel_poster_png(html_path, png_path)`，可以使用 Playwright 或项目可用的浏览器渲染器。如果当前环境没有 Playwright，就只增最小必要依赖，并在实现说明里记录安装命令。

预期输出：

- `poster.html`
- `poster.png`

- [ ] **步骤 4：运行海报测试**

运行：

```powershell
.\.venv\Scripts\python -m pytest backend\tests\test_poster_generator.py -q
```

预期：通过。

### 任务 4：新增平行 `poster-generator` subagent

- [ ] **步骤 1：增加 prompt**

在 `backend\src\personalops_agent\agent\prompts.py` 中新增：

```python
POSTER_SYSTEM_PROMPT = """
你是 DeepAgent PersonalOps Platform 的 Poster Generator subagent。
你的唯一任务，是把现有的旅行计划或旅行 brief 转成竖版中文信息图海报。
不要自己去查天气、汇率、地图或 POI。
生成海报时请使用 travel-poster skill，并保留旅行 brief 里的事实信息。
"""
```

- [ ] **步骤 2：更新 factory 测试**

在 `backend\tests\test_agent_factory.py` 中断言：

```python
assert [subagent["name"] for subagent in captured["subagents"]] == [
    "travel-planner",
    "ppt-generator",
    "poster-generator",
]
assert captured["subagents"][2]["tools"] == []
assert captured["subagents"][2]["skills"] == ["/skills/travel-poster/"]
```

- [ ] **步骤 3：更新 factory**

加入：

```python
{
    "name": "poster-generator",
    "description": "将既有旅行规划转换为竖版中文信息海报。",
    "system_prompt": POSTER_SYSTEM_PROMPT,
    "tools": [],
    "skills": ["/skills/travel-poster/"],
}
```

- [ ] **步骤 4：运行聚焦测试**

运行：

```powershell
.\.venv\Scripts\python -m pytest backend\tests\test_agent_factory.py backend\tests\test_poster_generator.py -q
```

预期：通过。

### 任务 5：复用现有 artifact UI 展示 poster

- [ ] **步骤 1：必要时增加前端测试**

如果 Phase 05 的 artifact 卡片已经是按通用 kind/filename/status 渲染，就只补一个回归测试即可：

```javascript
expect(renderedArtifact.kind).toBe('poster_png')
```

- [ ] **步骤 2：必要时补一个图片预览**

如果现有 artifact 卡片只支持下载链接，可以考虑为 `poster_png` 加一个轻量的图片预览。但这一步一定要保持很小，不要顺便重做聊天 UI。

- [ ] **步骤 3：运行前端检查**

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

手工浏览器测试：

1. 启动 MongoDB、后端和前端。
2. 先生成一份旅行规划。
3. 再输入：`把刚才的旅行规划生成一张竖版海报。`
4. 确认页面里出现海报 artifact 卡片。
5. 打开或下载 PNG。
6. 手工检查海报的中文是否清楚、层次是否分明、信息密度是否接近参考图方向。

回归测试：

1. 再输入：`把刚才的旅行规划生成 PPT。`
2. 确认 PPT artifact 流仍然正常。

## 人工验收清单

- [ ] `travel-planner`、`ppt-generator` 和 `poster-generator` 是平行 subagent。
- [ ] `poster-generator` 没有天气、汇率或 AMap 工具。
- [ ] `travel-poster` skill 已存在。
- [ ] poster artifact 复用现有 artifact API。
- [ ] poster PNG 可读，视觉方向接近密集型中文信息图。
- [ ] PPT artifact 流仍然可用。

## 停止点

本阶段通过后先停下来，让你检查 PPT 和海报两条流程。Sandbox 迁移应作为后续独立阶段。
