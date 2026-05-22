# Implementation Plan — Session 6 Agent

13 steps. Each step = one deliverable file. Exit criteria = concrete verifiable condition. No step advances until criteria met.

---

## Step 0 — Environment baseline

Verify substrate before any code.

- `curl :8101/v1/capabilities` returns 200, gemini present.
- `uv run python mcp_server.py` starts, no traceback (Ctrl-C to stop).
- `state/` dir exists, empty.

**Exit:** gateway reachable + MCP server boots clean.

---

## Step 1 — `schemas.py`

Pydantic v2 contracts. Two layers.

**Internal:** `MemoryItem`, `Artifact`, `Goal`, `Observation` (+`all_done` prop, `next_unfinished()`), `ToolCall`, `DecisionOutput` (+`is_answer` prop).

**Wire:** `PerceivedGoal` (`text`, `done`, `artifact_index:int|None` — no id), `PerceptionResponse` (`goals:list`), `MemoryClassification` (`kind`, `keywords`, `descriptor`, `value`, `confidence`).

**Exit:**
- `uv run python -c "import schemas"` — no error.
- `Observation(goals=[Goal(id='g1',text='x',done=True)]).all_done is True`.
- `DecisionOutput(answer='hi').is_answer is True`; `DecisionOutput(tool_call=ToolCall(name='t',arguments={})).is_answer is False`.
- `PerceptionResponse.model_json_schema()` returns dict with `goals` array.

---

## Step 2 — `artifacts.py`

`ArtifactStore`: `put(blob,*,content_type,source,descriptor)->str`, `get_bytes`, `get_meta`, `exists`. Handle `art:<sha256[:16]>`. Files `state/artifacts/<id>.bin`+`.json`.

**Exit:**
- `put(b"hello",...)` returns `art:`-prefixed string; two files written.
- `get_bytes(id) == b"hello"`; `get_meta(id)` is valid `Artifact`.
- Sequential ids: `art:0001`, `art:0002`, … (counter in `state/artifacts/_counter.json`).
- `exists("art:bogus") is False`.

---

## Step 3 — `memory.py`

`Memory` service over `state/memory.json`.

- `read(query,history,kinds=None,top_k=8)` — keyword overlap, stopword filter, no LLM.
- `filter(kinds=,goal_id=,recent=N)` — no LLM.
- `relevant(query,kinds=,top_k=5)` — `auto_route="memory"`.
- `remember(raw_text,source,run_id,goal_id=None)` — classify call (`provider="g"`, `response_format=MemoryClassification`).
- `record_outcome(tool_call,result_text,artifact_id,run_id,goal_id)` — no LLM, keywords from tool name+args.
- Load on init, save after every mutation.

**Exit:**
- `remember("My mom's birthday is 15 May 2026", source="test", run_id="r1")` → returns `MemoryItem` kind=`fact`, keywords include `mom`/`birthday`, `value` holds the date.
- After remember, `state/memory.json` exists, parses, contains the item.
- Fresh `Memory()` instance → `read("when is mom birthday", [])` returns that item ≥1 hit.
- `read` runs with zero gateway calls (verify: works with stub / no router_decision side effects).
- `record_outcome` appends `tool_outcome` item, no LLM call.

---

## Step 4 — `action.py`

`async execute(session, tool_call) -> tuple[str, str|None]`.

- Guard: `arguments` `path`/`url` starting `art:` → return error string, `None`, no dispatch.
- Else `session.call_tool` → collapse content blocks → text.
- `len(text.encode()) > 4096` → `ArtifactStore.put`, return `[artifact art:..., N bytes] preview: ...`, art_id. Else return text, `None`.

**Exit:**
- `execute(session, ToolCall(name="get_time",arguments={"timezone":"UTC"}))` → descriptor str, `None`.
- `execute(session, ToolCall(name="fetch_url",arguments={"url":"art:abc"}))` → error string mentioning artifact handle, `None`, MCP not called.
- Large payload (`fetch_url` real page) → returns `[artifact art:...]` descriptor + non-None art_id; artifact file on disk.

---

## Step 5 — `prompts/`

`perception.txt`, `decision.txt`, `memory_classify.txt`. Perception = 4 obligations (decompose / sticky-done / attach / preserve order). Decision = 3 rules (one output, `art:` not a path, substantive ≥3 sentences).

**Exit:**
- Three files exist, non-empty.
- Perception prompt text contains all 4 obligations; Decision contains all 3 rules.

---

## Step 6 — `perception.py`

`observe(query,hits,history,prior_goals,run_id) -> Observation`.

- Build prompt: query + indexed memory hits + history + prior goals.
- Call: `provider="g"`, `temperature=1.0`, `response_format=PerceptionResponse`.
- Map wire→internal: positional id carry-over from `prior_goals`; new goals get fresh ids; `artifact_index`→real handle; sticky-done (prior done stays done); synthesis force-attach.

**Exit:**
- First call (`prior_goals=[]`) on Query A text → `Observation` with ≥2 goals, all `done=False`.
- Second call with history containing a satisfying action → that goal `done=True`, others preserved, same count, same order.
- Goal with `artifact_index` set in wire output → internal `Goal.attach_artifact_id` is a real `art:` handle from hits (or `None` if index invalid).
- Goal ids stable across two consecutive `observe` calls.

---

## Step 7 — `decision.py`

`next_step(goal,hits,attached,history,mcp_tools) -> DecisionOutput`.

- Prompt: goal + hits + history + `ATTACHED ARTIFACTS:` section when `attached` non-empty.
- Call: `auto_route="decision"`, flat `tools=mcp_tools`, `tool_choice="auto"`.
- `tool_calls[]` present → `DecisionOutput(tool_call=ToolCall(first))`; else → `DecisionOutput(answer=text)`.

**Exit:**
- Goal "fetch wikipedia page for X", no attachment → returns `DecisionOutput` with `tool_call` name=`fetch_url`.
- Goal "extract dates" with artifact bytes attached → returns `DecisionOutput` with `answer`, ≥3 sentences.
- Exactly one of `answer`/`tool_call` populated every call.

---

## Step 8 — `agent6.py`

`ensure_gateway`, `mcp_session` (mcp 1.27.1 stdio `ClientSession` → `mcp_server.py`), `load_tools`, `mcp_tools_for_decision` (MCP schema → flat gateway tool), `run(query)` loop, `final_answer_from(history)`, `MAX_ITERATIONS=15`. CLI `python agent6.py "query"`.

**Exit:**
- `uv run python agent6.py "what time is it in UTC"` → completes, prints a final answer, no traceback.
- Loop terminates via `obs.all_done` (not via `MAX_ITERATIONS` exhaustion) on that trivial query.
- `state/memory.json` written after run.

---

## Step 9 — Query A (Shannon Wikipedia)

Clean state. `rm -rf state/memory.json state/artifacts/`.

**Exit:**
- Final answer contains birth date **April 30, 1916** + death date **February 24, 2001** + 3 information-theory contributions.
- Iterations ≤ 6 (2× expected 3).
- iter 2 shows artifact attach (`attach=art:...`).

---

## Step 10 — Query B (Tokyo weather)

Clean state.

**Exit:**
- Final answer picks 1 of 3 activities, justified by Saturday weather.
- Iterations ≤ 12 (2× expected 6).
- Weather fact from action carried into final Decision via memory read.

---

## Step 11 — Query C (Mom's birthday — durable memory)

Clean state. Two runs, same `state/`.

**Exit:**
- Run 1: reminders created in sandbox; iterations ≤ 8 (2× expected 4).
- `state/memory.json` after run 1 holds `fact` item with the date.
- Run 2 (`"When is mom's birthday?"`): answers **15 May 2026**; iterations ≤ 4 (2× expected 2); answer sourced from memory, not re-derived.

---

## Step 12 — Query D (asyncio synthesis)

Clean state.

**Exit:**
- Final answer = numbered list of agreed advice from multiple sources.
- Iterations ≤ 14 (2× expected 7).
- ≥2 artifacts created from fetches; synthesis goal got an attachment.

---

## Step 13 — Deliverables

- `.gitignore` += `state/`.
- `README.md` rewritten: per-query run commands + verbatim clean-state terminal output of all 4.
- PoP validation JSON: run `docs/eval_prompt.md` evaluator over `prompts/perception.txt` + `prompts/decision.txt`, save JSON review.
- YouTube — you record (out of scope).

**Exit:**
- `git status` — `state/` untracked-ignored, not staged.
- README has 4 output blocks, each from a clean run.
- PoP JSON parses, has all 9 eval keys.
