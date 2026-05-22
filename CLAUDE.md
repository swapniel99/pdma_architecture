# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Context

EAG3-06 (Session 6) assignment: build a multi-role cognitive agent using four modules (`memory.py`, `perception.py`, `decision.py`, `action.py`) wired together in `agent6.py`. The MCP server (`mcp_server.py`) and LLM gateway client (`client.py`) are already provided.

## Commands

```bash
# Run MCP server (stdio transport — used by agent loop internally)
uv run python mcp_server.py

# Run agent against a query
uv run python agent6.py "your query here"

# Dev REPL
uv run ipython

# Reset state between runs
bash clear_state.sh
# or: rm -rf state/memory.json state/artifacts/
```

Requires Python ≥ 3.14. Required env vars in `.env`:
- `TAVILY_API_KEY` — web search primary

## Architecture

### Four cognitive roles

| Module | Role | LLM cost |
|---|---|---|
| `memory.py` | Typed KV store. `read(query, history)` = keyword search, no LLM. `remember(text)` = one classification call. `record_outcome(tool_call, result)` = no LLM. | Only on ambiguous writes |
| `perception.py` | Orchestrator. Emits `Observation` (goal list + done flags). Pinned to Gemini via `provider="g"`, `temperature=1.0`. | Every iteration |
| `decision.py` | Returns `DecisionOutput`: either `answer` (str) or `tool_call` (ToolCall). One goal per call, never both outputs. | Every iteration |
| `action.py` | Pure MCP dispatch. Stores payloads >4 KB in `ArtifactStore`; returns descriptor. No LLM. | Never |

### Key invariants
- **No free-form dicts between roles** — every boundary is a Pydantic v2 model from `schemas.py`
- **No direct SDK calls** — all LLM calls go through gateway at `http://localhost:8101` via `client.py`
- **No third-party agent frameworks** (LangChain, LangGraph, CrewAI)
- **Perception owns done-marking** — Decision never declares a goal satisfied
- **Artifact handles** (`art:<NNNN>`) are not paths; Action blocks any tool call that passes one as `path` or `url`
- **Goals have positional identity** — Perception preserves list order across iterations; no string-id hallucination

### State persistence
- `state/memory.json` — all MemoryItems (facts, preferences, tool_outcomes, scratchpad)
- `state/artifacts/<id>.bin` + `<id>.json` — raw bytes + metadata for large tool outputs
- Clean between attempts: `rm -rf state/memory.json state/artifacts/`

### Main loop sketch (`agent6.py`)
```
memory.remember(query)          # classify & persist user facts
for iter in range(MAX_ITER):
    hits = memory.read(query, history)
    obs  = perception.observe(query, hits, history, prior_goals, run_id)
    if obs.all_done: break
    goal = obs.next_unfinished()
    attached = [artifacts.get_bytes(goal.attach_artifact_id)] if goal.attach_artifact_id else []
    out  = decision.next_step(goal, hits, attached, history, tools)
    if out.is_answer:
        history.append({"kind": "answer", ...}); continue
    result_text, art_id = await action.execute(session, out.tool_call)
    memory.record_outcome(...)
    history.append({"kind": "action", ...})
```

### LLM Gateway V3 (`client.py`)
- Base URL: `http://localhost:8101` (env: `LLM_GATEWAY_V3_URL`)
- `auto_route="perception"|"memory"|"decision"` — gateway routes to appropriate tier
- `provider="g"` — skip router, force Gemini (used by Perception)
- Response includes `router_decision.fallback_used` and `reasoning_applied` for observability

### Supporting modules
- `artifacts.py` — `ArtifactStore`: sequential byte store; `put()` returns `art:<NNNN>` handle (counter in `state/artifacts/_counter.json`); files land in `state/artifacts/<id>.{bin,json}`
- `prompts/` — raw text files loaded by each role at import time: `decision.txt`, `memory_classify.txt`, `perception.txt`

### Pydantic contracts (`schemas.py`)
```python
MemoryItem(id, kind, keywords, descriptor, value, artifact_id, source, run_id, goal_id, confidence, created_at)
Artifact(id, content_type, size_bytes, source, descriptor)
Goal(id, text, done, attach_artifact_id)
Observation(goals)           # + property: all_done, next_unfinished()
ToolCall(name, arguments)
DecisionOutput(answer, tool_call)   # exactly one populated
```

### MCP tools (9 total in `mcp_server.py`)
`web_search`, `fetch_url`, `get_time`, `currency_convert`, `read_file`, `list_dir`, `create_file`, `update_file`, `edit_file`

File tools are sandboxed under `./sandbox/`. `fetch_url` uses crawl4ai (headless Chromium). `web_search` uses Tavily primary / DuckDuckGo fallback, hard-capped at 5 results, with monthly usage tracking in `usage.json`.

## Four target queries

| Query | Key behaviour exercised | Expected iterations |
|---|---|---|
| A: Claude Shannon Wikipedia | Artifact attach — fetch then extract from 250KB page | 3 |
| B: Tokyo weekend activities | Multi-goal + weather memory carryover | ~6 |
| C: Mom's birthday (2 runs) | Durable memory across runs; run 1 writes fact, run 2 reads it | 4 / 2 |
| D: asyncio best practices | Multi-artifact fetch + synthesis | 5–7 |

Queries exceeding **2× expected iteration count** are not passing — tune prompts.
