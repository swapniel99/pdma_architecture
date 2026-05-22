# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Context

EAG3-06 (Session 6) assignment: build a multi-role cognitive agent using four modules (`memory.py`, `perception.py`, `decision.py`, `action.py`) wired together in `agent.py`. The MCP server (`mcp_server.py`) and LLM gateway client (`client.py`) are already provided.

## Commands

```bash
# Install dependencies
uv sync

# Run agent against a query (LLM Gateway must already be running at localhost:8101)
uv run python agent.py "your query here"

# Run a named target query (a/b/c1/c2/d) — reads from queries/query_<id>.txt
./run_query.sh <a|b|c1|c2|d>
./run_query.sh c2 --no-clear   # preserve C1 memory for C2

# Reset state between runs (clears state/memory.json, state/artifacts/, sandbox/*)
bash clear_state.sh

# Run MCP server standalone (normally launched internally by agent loop via stdio)
uv run python mcp_server.py
```

Requires Python ≥ 3.14. Required env vars in `.env`:
- `TAVILY_API_KEY` — web search primary

**Prerequisite:** LLM Gateway V3 must be running at `http://localhost:8101` before starting the agent. The agent does not launch it.

## Architecture

### Four cognitive roles

| Module | Role | LLM cost |
|---|---|---|
| `memory.py` | Typed KV store. `read(query, history)` = keyword search, no LLM. `remember(text)` = one classification call. `record_outcome(tool_call, result)` = no LLM. | Only on ambiguous writes |
| `perception.py` | Orchestrator. Emits `Observation` (goal list + done flags). Pinned to Gemini via `provider="g"`, `temperature=1.0`. | Every iteration |
| `decision.py` | Returns `DecisionOutput`: either `answer` (str) or `tool_call` (ToolCall). One goal per call, never both outputs. Retries up to 3× with 3 s sleep on gateway error. | Every iteration |
| `action.py` | Pure MCP dispatch. Stores payloads >4 KB in `ArtifactStore`; returns descriptor. No LLM. | Never |

### Key invariants
- **No free-form dicts between roles** — every boundary is a Pydantic v2 model from `schemas.py`
- **No direct SDK calls** — all LLM calls go through gateway at `http://localhost:8101` via `client.py`
- **No third-party agent frameworks** (LangChain, LangGraph, CrewAI)
- **Perception owns done-marking** — Decision never declares a goal satisfied
- **Artifact handles** (`art:<NNNN>`) are not paths; Action blocks any tool call that passes one as `path` or `url`
- **Goals have positional identity** — Perception preserves list order across iterations; no string-id hallucination
- **Sticky-done** — once a goal is marked done in `prior_goals`, Perception keeps it done regardless of its own output

### Auto-attach behavior (`agent.py`)
If a goal has no explicit `attach_artifact_id` from Perception, `agent.py` auto-attaches based on goal text:
- Goal matches `_FETCH_NTH_KEYWORDS` ("fetch the 1st/2nd/3rd search result") → attach most recent **web_search** artifact so Decision can read URLs
- Goal matches `_ANALYSIS_KEYWORDS` ("extract", "identify", "summarize", "determine", "compare", "based on the", etc.) → attach most recent **any action** artifact
- Otherwise no auto-attach

This means analysis goals and "Fetch Nth" goals always receive relevant content without Perception needing to wire `artifact_index` explicitly.

### Final answer synthesis
`_synthesize_final_answer` always runs after the loop exits (whether via `all_done`, `MAX_ITERATIONS=15`, or no unfinished goals). It scans history for tool results and partial answers, loads full artifact bytes (up to 6 000 chars), and calls the gateway (`auto_route="decision"`) to produce a complete response.

### State persistence
- `state/memory.json` — all MemoryItems (facts, preferences, tool_outcomes, scratchpad)
- `state/artifacts/<id>.bin` + `<id>.json` — raw bytes + metadata for large tool outputs
- `usage.json` — monthly Tavily search count (hard-capped at 5 results per call)
- Clean between attempts: `bash clear_state.sh` (also wipes `sandbox/*`)

### Main loop sketch (`agent.py`)
```
memory.remember(query)          # classify & persist user facts
for iter in range(MAX_ITERATIONS):   # MAX_ITERATIONS = 15
    hits = memory.read(query, history)
    obs  = perception.observe(query, hits, history, prior_goals, run_id)
    if obs.all_done: break
    goal = obs.next_unfinished()
    # auto-attach last fetch_url artifact if goal has no explicit attachment
    attached = [artifacts.get_bytes(attach_id)] if attach_id else []
    out  = decision.next_step(goal, hits, attached, history, tools)
    if out.is_answer:
        history.append({"kind": "answer", ...}); continue
    result_text, art_id = await action.execute(session, out.tool_call)
    memory.record_outcome(...)
    history.append({"kind": "action", ...})
return await _synthesize_final_answer(query, history, mem)
```

### LLM Gateway V3 (`client.py`)
- Base URL: `http://localhost:8101` (env: `LLM_GATEWAY_V3_URL`)
- `auto_route="perception"|"memory"|"decision"` — gateway routes to appropriate tier
- `provider="g"` — skip router, force Gemini (used by Perception)
- Response includes `router_decision.fallback_used` and `reasoning_applied` for observability

### Supporting modules
- `artifacts.py` — `ArtifactStore`: sequential byte store; `put()` returns `art:<NNNN>` handle (counter in `state/artifacts/_counter.json`); files land in `state/artifacts/<id>.{bin,json}`
- `prompts/` — raw text files loaded by each role at import time: `decision.txt`, `memory_classify.txt`, `perception.txt`
- `queries/query_<id>.txt` — actual query text for each target (read by `run_query.sh`)
- `pop_validation.json` — prompt evaluation scores for the three prompts (criteria: structured output, reasoning, tool separation, etc.)

### Pydantic contracts (`schemas.py`)

Inter-role contracts (passed between modules):
```python
MemoryItem(id, kind, keywords, descriptor, value, artifact_id, source, run_id, goal_id, confidence, created_at)
Artifact(id, content_type, size_bytes, source, descriptor)
Goal(id, text, done, attach_artifact_id)
Observation(goals)           # + property: all_done, next_unfinished()
ToolCall(name, arguments)
DecisionOutput(answer, tool_call)   # exactly one populated
```

Wire models (LLM `response_format` only — never passed between roles):
```python
PerceivedGoal(text, done, artifact_index)    # perception LLM output; artifact_index resolved to art: handle
PerceptionResponse(goals)                    # wraps list[PerceivedGoal]
MemoryClassification(kind, keywords, descriptor, value, confidence)  # memory LLM output
```

### Memory API
- `read(query, history, kinds?, top_k=8)` — keyword overlap score, no LLM
- `filter(kinds?, goal_id?, recent?)` — structured filter without scoring
- `remember(text, source, run_id, goal_id?)` — one LLM call to classify
- `record_outcome(tool_call, result_text, artifact_id, run_id, goal_id?)` — no LLM

### MCP tools (9 total in `mcp_server.py`)
`web_search`, `fetch_url`, `get_time`, `currency_convert`, `read_file`, `list_dir`, `create_file`, `update_file`, `edit_file`

File tools are sandboxed under `./sandbox/`. `fetch_url` uses crawl4ai (headless Chromium). `web_search` uses Tavily primary / DuckDuckGo fallback, hard-capped at 5 results, with monthly usage tracking in `usage.json`.

## Four target queries

| Query | Key behaviour exercised | Expected iterations | Limit (2×) |
|---|---|---|---|
| A: Claude Shannon Wikipedia | Explicit URL fetch → extract from 270KB artifact | 3 | 6 |
| B: Tokyo weekend activities | Multi-goal, weather search, determine best activity | ~8 | 12 |
| C1: Mom's birthday (run 1) | Action query — creates 2 reminder files, stores fact in memory | ~4 | 8 |
| C2: Mom's birthday (run 2) | MEMORY-SUFFICIENT RULE — answers from memory, no tools | 2 | 4 |
| D: asyncio best practices | Pattern B — list URLs, fetch 3 pages, extract each, synthesise | ~10 | 14 |

Run with `./run_query.sh <a|b|c1|c2|d>`. Use `--no-clear` for C2 (must preserve C1 memory).
Queries exceeding limit are not passing — tune prompts.
