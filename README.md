# DeepAgent PersonalOps Platform

一个基于 LangChain / LangGraph / DeepAgents 的可扩展多子 Agent 平台。第一条业务能力是旅行规划子 Agent，用于日常真实使用，也用于展示企业级 Agent 应用开发能力。

`D:\AIProject\deep_agent\ERP_OPENCLAW` 是参考项目，本项目独立开发，不修改参考项目。

## 当前能力

- FastAPI 后端
- Vue 聊天前端
- DeepSeek 真实 LLM 配置
- DeepAgents 主 Agent + Travel Planner 子 Agent 工厂
- 智谱联网搜索工具：`POST /api/paas/v4/web_search`
- AMap Maps MCP 可选加载：`https://mcp.amap.com/mcp?key=...`
- 天气、汇率工具封装
- MongoDB 优先持久化，会话可回退到内存存储
- SSE 流式输出：`token`、`tool_start`、`tool_args`、`tool_result`、`done`、`error`
- 工具缺少 API Key 时明确报错，不伪造外部数据

## 本地启动

1. 准备环境变量：

```powershell
Copy-Item .env.example .env
```

填写：

- `DEEPSEEK_API_KEY`
- `ZHIPU_API_KEY`
- `AMAP_MAPS_API_KEY`
- `WEATHER_API_KEY`
- `EXCHANGE_RATE_API_KEY`

其中 `ZHIPU_BASE_URL` 默认是：

```text
https://open.bigmodel.cn/api/paas/v4/
```

2. 启动 MongoDB：

```powershell
docker compose up mongo
```

如果只是临时测试 LLM 和工具、不想启动 MongoDB，可以在 `.env` 中设置：

```text
MONGODB_URI=memory://
```

3. 启动后端：

```powershell
cd backend
pip install -e .[dev]
uvicorn personalops_agent.main:app --reload --host 0.0.0.0 --port 8000
```

4. 启动前端：

```powershell
cd frontend
npm install
npm run dev
```

打开 `http://localhost:5173`。

## Docker 启动

```powershell
Copy-Item .env.example .env
docker compose up --build
```

## API

- `GET /api/health`
- `POST /api/chat/stream`
- `GET /api/sessions`
- `GET /api/sessions/{thread_id}`

## 旅行工具说明

- `search_web` 使用智谱联网搜索，适合查询目的地、景点、餐厅、交通和近期活动。
- `get_weather` 使用天气 API，适合补充目的地天气。
- `convert_currency` 使用汇率 API，适合跨境预算换算。
- AMap MCP 工具通过 `langchain-mcp-adapters` 动态加载，适合地理编码、POI、路线规划、距离和地图天气等旅行场景。

AMap MCP 参考：

- ModelScope: `https://www.modelscope.cn/mcp/servers/@amap/amap-maps`
- npm: `@amap/amap-maps-mcp-server`

## 面试讲解重点

- 不是单一旅行聊天机器人，而是可扩展的 DeepAgents 平台。
- Travel Planner 只是第一个子 Agent，后续可以加入求职助手、学习助手、PlatformOps 助手。
- 搜索使用智谱联网搜索，地图能力通过 AMap MCP 接入，体现真实工具生态集成。
- 工具调用全部走真实 API；缺配置时明确失败，不伪造结果。
- 架构保留了企业级 Agent 常见要素：多 Agent 编排、工具调用、持久化、审计入口、流式 UI、环境隔离和 Docker 部署。

## 测试

后端：

```powershell
cd backend
python -m pytest tests -q
ruff check src tests
```

前端：

```powershell
cd frontend
npm test
npm run build
```
