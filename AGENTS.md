# AGENTS.md

This file is the durable project guidance for Codex and other coding agents working on
`personalops-agent`.

## Project Identity

- This is `DeepAgent PersonalOps Platform`, an extensible AI agent application.
- The primary purpose of this repository is learning and interview demonstration for AI
  agent application development. Every feature should help explain real agent engineering:
  architecture, tool use, streaming, state, persistence, safety, and production thinking.
- Current stack: FastAPI + LangChain + DeepAgents backend, Vue + Vite frontend, MongoDB
  storage, SSE streaming, DeepSeek LLM, Zhipu web search, optional AMap MCP, weather, and
  exchange-rate tools.
- The first business capability is Travel Planner. Treat it as the first sub-agent in a
  broader PersonalOps platform, not as a one-off travel chatbot.
- `D:\AIProject\deep_agent\ERP_OPENCLAW` is a read-only reference project. You may inspect it
  for architecture, UX, tool-status display, and enterprise patterns, but never modify files
  under `ERP_OPENCLAW`.
- DeepAgents implementation work must reference the official docs first:
  `https://docs.langchain.com/oss/python/deepagents`.

## Required Start-Of-Task Routine

Before changing code, do all of the following:

1. Use Superpowers. Read and follow the relevant Superpowers skills for the task, especially
   debugging, TDD, code review, frontend verification, or planning skills when they apply.
2. Identify the development phase for the current task.
3. Find and read the matching phase plan before implementation.
4. State the phase and plan file used in the working notes or final response.
5. For DeepAgents features, read the relevant official DeepAgents docs page before changing
   code and mention the page used.

Use this plan discovery order:

- Search with `rg --files | rg "(plan|phase|roadmap|spec)"`.
- Prefer `docs/plans/phase-*.md`, `docs/superpowers/**`, `PLANS.md`, or README sections that
  explicitly describe phased development.
- If no matching plan exists, say so clearly. For substantial feature work, create or ask for
  a phase plan first. For narrow bug fixes, make a short local plan in the response and keep
  the change tightly scoped.

Phase classification guide:

- Phase 0: project setup, environment, dependency, Docker, MongoDB, local run reliability.
- Phase 1: minimal DeepAgent foundation: `create_deep_agent`, model wiring, prompts,
  one subagent, and deterministic API/SSE shell.
- Phase 2: tools and MCP: typed first-party tools plus AMap MCP using the official
  DeepAgents tools/MCP guidance.
- Phase 3: backend/filesystem capability: introduce DeepAgents backend concepts such as
  `StateBackend`, `StoreBackend`, or a carefully scoped filesystem backend.
- Phase 4: streaming UX: SSE events, frontend aggregation, tool progress rendering, and
  DeepAgents streaming concepts.
- Phase 5: persistence and memory: sessions, replay, long-term memory, user/thread scoping,
  and MongoDB/LangGraph storage boundaries.
- Phase 6: sandbox and execution: isolated execution backend, sandbox tool display, file
  transfer, and artifact retrieval. Do not use host shell execution in an HTTP/API context.
- Phase 7: safety and production readiness: permissions, human-in-the-loop, evals,
  observability, security, auth, deployment, and CI.
- Phase 8: product expansion: additional subagents or PersonalOps workflows beyond Travel
  Planner.

## Incremental Phase Rule

- Do not implement multiple DeepAgents core capabilities in one pass just because the docs
  list them together.
- Each phase should add one coherent capability, with tests and a manual verification path.
- After finishing a phase, stop. The user must test and adjust before the next phase starts.
- If a request tries to jump ahead, name the current phase, explain the skipped dependency,
  and propose the smallest next phase instead.

## Engineering Workflow

- Read the relevant code first. Let the existing structure guide the change.
- Prefer TDD for behavior changes: write or update a focused failing test, confirm it fails,
  implement the smallest fix, then run the relevant suite.
- Keep changes scoped. Do not bundle unrelated refactors, formatting churn, or metadata edits.
- Preserve structured backend events and let the frontend aggregate UI state.
- Do not fake external tool data. If an API key or service is unavailable, return a clear
  failure or configuration message.
- Treat `.env.example` as safe documentation. Never expose real secrets in committed files.
- Use `apply_patch` for manual edits.
- Do not revert user changes or run destructive git commands unless explicitly requested.

## Commands

Backend:

```powershell
cd D:\AIProject\deep_agent\personalops-agent
.\.venv\Scripts\python -m pytest backend\tests -q
cd backend
ruff check src tests
uvicorn personalops_agent.main:app --reload --host 0.0.0.0 --port 8000
```

Frontend:

```powershell
cd D:\AIProject\deep_agent\personalops-agent\frontend
npm test
npm run build
npm run dev
```

MongoDB:

```powershell
cd D:\AIProject\deep_agent\personalops-agent
docker compose up mongo
```

Use `MONGODB_URI=memory://` only for explicit local in-memory debugging. Otherwise backend
startup should fail clearly when MongoDB is required but unavailable.

## Agent Application Practices

- Keep agent boundaries explicit: prompts, tools, schemas, storage, API streaming, and frontend
  rendering should remain separately testable.
- Preserve the project as an interview narrative. Code should make it easy to explain what
  problem each DeepAgents capability solves and why it was added in that phase.
- Prefer small, typed tool contracts over ad hoc string parsing.
- Tool-call streaming should remain structured: start, args delta, result, error, done.
- Frontend should group intermediate process by user turn, not as a detached global log.
- Add or update regression tests for tool argument streaming, tool result correlation, storage,
  and user-facing error messages when those behaviors change.
- For production-facing agent work, consider observability and evals: traces, tool calls,
  latency, failures, scenario tests, and human review points.

DeepAgents capabilities to cover over time, one phase at a time:

- Planning and task decomposition with `write_todos`.
- Tools and MCP integration.
- Pluggable backends and virtual filesystem behavior.
- Subagents for context isolation and specialized work.
- Streaming and event projections.
- Long-term memory.
- Filesystem permissions.
- Human-in-the-loop approvals.
- Skills or reusable workflows.
- Sandboxes for isolated code/file/shell execution.

Do not add sandbox, backend, memory, permissions, HITL, skills, and deployment hardening all
at once. Treat them as separate learning/demo milestones.

## Frontend Rules

- Preserve the current Vue/Vite app style unless the task is explicitly redesigning UI.
- For chat UX, prioritize readable message flow, collapsible execution process, stable layout,
  and no raw JSON dumps unless the user asks for debugging output.
- Verify meaningful frontend changes with tests and, when a dev server is running, browser
  inspection for console errors and visual regressions.

## Completion Standard

A task is done only when:

- The requested behavior is implemented or the blocker is clearly identified.
- Relevant tests/builds have been run, or the reason they could not be run is stated.
- The final response names the phase, the plan source used, and the verification performed.
- Any needed user action, such as restarting backend/frontend or supplying an API key, is
  stated plainly.
