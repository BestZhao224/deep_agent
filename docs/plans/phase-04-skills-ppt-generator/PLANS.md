# Skills 与 PPT 生成 subagent 实施计划

> **给执行该计划的智能体：** 必须使用 `superpowers:subagent-driven-development`（推荐）或 `superpowers:executing-plans`，按任务逐步执行。步骤使用勾选框 `- [ ]` 记录进度。

**目标：** 在 backend 基础上集成 DeepAgents skills，并新增与 `travel-planner` 平行的 `ppt-generator` subagent。

**架构：** `travel-planner` 继续负责旅行规划；`ppt-generator` 是独立的 PPT 专家 subagent，只消费旅行计划或旅行 brief，并生成 PowerPoint。因为自定义 DeepAgents subagent 不会自动继承主 agent skills，所以 `ppt-generator` 必须显式配置 `skills=["/skills/travel-pptx/"]`。本阶段只验证 skills 和 PPT 的本地生成，不开放 artifact 下载 API，也不做前端 artifact 卡片。

**技术栈：** DeepAgents subagents、DeepAgents skills、FastAPI backend、`python-pptx`、pytest。

---

## 参考资料

- 依赖上一个计划：`D:\AIProject\deep_agent\personalops-agent\docs\plans\phase-03-backend-integration\PLANS.md`
- 官方文档：<https://docs.langchain.com/oss/python/deepagents/skills>
- 官方文档：<https://docs.langchain.com/oss/python/deepagents/subagents>
- 公开 skill 参考：`anthropics/skills/pptx`
- 只读参考项目：`D:\AIProject\deep_agent\ERP_OPENCLAW`

## 范围边界

- 不新增 artifact API。
- 不新增前端 artifact 卡片。
- 不新增海报生成。
- 不把 PPT 生成迁移到 sandbox。
- 不把天气、汇率或 AMap 工具给 `ppt-generator`。

## 涉及文件

- 新建：`D:\AIProject\deep_agent\personalops-agent\backend\skills\travel-pptx\SKILL.md`
- 新建：`D:\AIProject\deep_agent\personalops-agent\backend\src\personalops_agent\artifacts\pptx.py`
- 新建：`D:\AIProject\deep_agent\personalops-agent\backend\tests\test_pptx_generator.py`
- 修改：`D:\AIProject\deep_agent\personalops-agent\backend\src\personalops_agent\agent\prompts.py`
- 修改：`D:\AIProject\deep_agent\personalops-agent\backend\src\personalops_agent\agent\factory.py`
- 修改：`D:\AIProject\deep_agent\personalops-agent\backend\tests\test_agent_factory.py`
- 修改：`D:\AIProject\deep_agent\personalops-agent\backend\pyproject.toml`

## 任务

### 任务 1：添加 PPT 依赖

- [ ] **步骤 1：加入 `python-pptx` 依赖**

修改 `backend\pyproject.toml` 的 dependencies：

```toml
"python-pptx>=1.0.2",
```

- [ ] **步骤 2：更新后端环境**

运行：

```powershell
cd D:\AIProject\deep_agent\personalops-agent\backend
..\.venv\Scripts\python -m pip install -e .[dev]
```

预期：依赖安装成功。

### 任务 2：创建 Travel PPT skill

- [ ] **步骤 1：新增 skill 文件**

创建 `backend\skills\travel-pptx\SKILL.md`，内容如下：

```markdown
---
name: travel-pptx
description: 根据结构化的旅行 brief 生成可编辑的 PowerPoint 演示文稿。
---

# Travel PPTX Skill

当用户要把旅行计划做成 PPT 时使用这个 skill。

## 输入

- 目的地
- 行程天数
- 预算
- 每日行程
- 美食与城市漫步亮点
- 交通说明
- 天气或风险提醒
- 来源说明

## 输出

生成一个可编辑的 `.pptx`，建议 5 到 7 页：

1. 封面
2. 旅行总览
3. 按天行程
4. 预算拆分
5. 交通与天气提醒
6. 美食与城市漫步亮点
7. 最终检查清单（如有需要）

## 风格

- 标题使用清晰中文。
- 尽量用简短 bullet，不要长段落。
- 每一页都必须可编辑。
- 不要编造旅行 brief 中没有的事实。
- 如果输入信息不够，仍然生成草稿，但要把假设说明清楚。
```

- [ ] **步骤 2：补一个 skill 存在性测试**

在 `backend\tests\test_agent_factory.py` 或新测试文件中加入：

```python
from pathlib import Path


def test_travel_pptx_skill_exists():
    skill = Path("backend/skills/travel-pptx/SKILL.md")
    assert skill.exists()
    text = skill.read_text(encoding="utf-8")
    assert "travel-pptx" in text
    assert ".pptx" in text
```

运行：

```powershell
.\.venv\Scripts\python -m pytest backend\tests\test_agent_factory.py::test_travel_pptx_skill_exists -q
```

预期：skill 文件存在后测试通过。

### 任务 3：添加确定性的 PPT 生成器

- [ ] **步骤 1：写一个会失败的 PPT 生成测试**

创建 `backend\tests\test_pptx_generator.py`：

```python
from personalops_agent.artifacts.pptx import TravelPptxBrief, create_travel_pptx


def test_create_travel_pptx_writes_real_file(tmp_path):
    brief = TravelPptxBrief(
        title="东京 5 天美食城市漫步",
        destination="东京",
        duration_days=5,
        budget="8000 人民币",
        overview="美食、城市漫步、公共交通优先。",
        daily_plan=[
            "Day 1: 抵达东京，浅草散步。",
            "Day 2: 上野与秋叶原。",
        ],
        budget_notes=["住宿 3000", "餐饮 2200"],
        reminders=["提前确认天气", "准备 Suica 或 Welcome Suica"],
    )

    output = create_travel_pptx(brief, tmp_path / "tokyo-plan.pptx")

    assert output == tmp_path / "tokyo-plan.pptx"
    assert output.exists()
    assert output.stat().st_size > 0
```

运行：

```powershell
.\.venv\Scripts\python -m pytest backend\tests\test_pptx_generator.py -q
```

预期：先失败，因为模块还没实现。

- [ ] **步骤 2：实现最小生成器**

创建 `backend\src\personalops_agent\artifacts\pptx.py`，实现一个 dataclass/Pydantic 模型和 `create_travel_pptx()` 函数，使用 `python-pptx` 生成文件。

最低要求：

- 生成封面页。
- 生成总览页。
- 生成按天行程页。
- 生成预算页。
- 生成提醒页。
- 保存到指定路径。

- [ ] **步骤 3：运行 PPT 生成测试**

运行：

```powershell
.\.venv\Scripts\python -m pytest backend\tests\test_pptx_generator.py -q
```

预期：测试通过，并在 pytest 临时目录里生成真实 PPTX。

### 任务 4：新增平行 `ppt-generator` subagent

- [ ] **步骤 1：增加 prompt**

在 `backend\src\personalops_agent\agent\prompts.py` 中新增：

```python
PPT_SYSTEM_PROMPT = """
你是 DeepAgent PersonalOps Platform 的 PPT Generator subagent。
你的唯一任务，是把现有的旅行计划或旅行 brief 转成可编辑的 PowerPoint。
不要自己去查天气、汇率、地图或 POI。
如果旅行信息缺失，就向协调者索取旅行计划，或者清楚标记假设。
生成 PPT 时请使用 travel-pptx skill。
"""
```

- [ ] **步骤 2：更新 factory 测试**

在 `backend\tests\test_agent_factory.py` 中更新断言：

```python
assert [subagent["name"] for subagent in captured["subagents"]] == [
    "travel-planner",
    "ppt-generator",
]
assert captured["subagents"][1]["tools"] == []
assert "PowerPoint" in captured["subagents"][1]["system_prompt"]
assert captured["subagents"][1]["skills"] == ["/skills/travel-pptx/"]
```

- [ ] **步骤 3：运行测试，确认先失败**

运行：

```powershell
.\.venv\Scripts\python -m pytest backend\tests\test_agent_factory.py -q
```

预期：在 `ppt-generator` 还没接入时失败。

- [ ] **步骤 4：在 factory 中加入 `ppt-generator`**

让 `subagents` 同时包含两个项：

```python
{
    "name": "travel-planner",
    "description": "...",
    "system_prompt": TRAVEL_SYSTEM_PROMPT,
    "tools": travel_tools,
},
{
    "name": "ppt-generator",
    "description": "将既有旅行规划转换为可编辑 PowerPoint 演示文稿。",
    "system_prompt": PPT_SYSTEM_PROMPT,
    "tools": [],
    "skills": ["/skills/travel-pptx/"],
}
```

这一阶段不要给主 `create_deep_agent(..., skills=...)` 配 skills；PPT skill 只属于自定义 `ppt-generator`。

- [ ] **步骤 5：运行聚焦测试**

运行：

```powershell
.\.venv\Scripts\python -m pytest backend\tests\test_agent_factory.py backend\tests\test_pptx_generator.py -q
```

预期：通过。

## 验证

运行：

```powershell
cd D:\AIProject\deep_agent\personalops-agent
.\.venv\Scripts\python -m pytest backend\tests -q
```

预期：后端测试通过。

手工检查 PPT：

- 用确定性生成器测试或临时脚本生成一个 PPTX。
- 用 PowerPoint / WPS 打开。
- 确认幻灯片可编辑，中文可读。

## 人工验收清单

- [ ] `travel-planner` 和 `ppt-generator` 是平行 subagent。
- [ ] `ppt-generator` 没有天气、汇率或 AMap 工具。
- [ ] `travel-pptx` skill 已存在，并说明了可复用的 PPT 工作流。
- [ ] 固定输入可以生成真实 `.pptx`。
- [ ] 此阶段还没有前端 artifact 卡片。
- [ ] 此阶段还没有 poster generator。

## 停止点

本阶段通过后先停下来，让你手工检查生成的 PPT。确认之后，再进入 Phase 05。
