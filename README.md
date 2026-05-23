# Session 6 Agent — Multi-Role Cognitive Agent

A multi-role cognitive agent built with four typed modules: `memory.py`, `perception.py`, `decision.py`, and `action.py`, wired together in `agent.py`. All LLM calls go through the LLM Gateway V3 (`localhost:8101`). Tool dispatch uses MCP stdio transport.

## Demo Video

📺 **[Watch the Multi-Role Cognitive Agent End-to-End Demo on YouTube](https://youtu.be/4zxG7htV3QU)**

## Prerequisites

- LLM Gateway V3 running at `http://localhost:8101`
- `.env` with `TAVILY_API_KEY`
- `uv` installed

## Run Commands

```bash
# Query A — Claude Shannon Wikipedia
./run_query.sh a

# Query B — Tokyo weekend activities
./run_query.sh b

# Query C — Mom's birthday (2 runs, same state/)
./run_query.sh c1
./run_query.sh c2 --no-clear   # --no-clear preserves C1 memory

# Query D — asyncio synthesis (Pattern B: fetch top 3 results)
./run_query.sh d
```

Actual queries are in `queries/query_<id>.txt`. `run_query.sh` resets state automatically unless `--no-clear` is passed.

---

## Query A — Claude Shannon Wikipedia

Clean state. Expected iterations: 3, limit: 6. **Actual: 4.**

```
$ ./run_query.sh a
State cleared.
Query [a]: Fetch https://en.wikipedia.org/wiki/Claude_Shannon and tell me his birth date, death date, and three key contributions to information theory.

─── iter 1 ───
[memory.read]   0 hits
[perception]    [open] Fetch https://en.wikipedia.org/wiki/Claude_Shannon
                [open] Extract his birth date, death date, and three key contributions to information theory from the fetched content
                [open] Answer the user: Fetch https://en.wikipedia.org/wiki/Claude_Shannon and tell me his birth date, death date, and three key contributions to information theory.
[decision]      TOOL_CALL: fetch_url({"url": "https://en.wikipedia.org/wiki/Claude_Shannon"})
[action]        → [artifact art:0001, 266693 bytes]

─── iter 2 ───
[memory.read]   1 hit
[perception]    [done] Fetch https://en.wikipedia.org/wiki/Claude_Shannon
                [open] Extract his birth date, death date, and three key contributions to information theory from the fetched content
                [open] Answer the user: Fetch https://en.wikipedia.org/wiki/Claude_Shannon and tell me his birth date, death date, and three key contributions to information theory.
[attach]        art:0001 (266693 bytes)
[decision]      ANSWER: Claude Shannon was born on April 30, 1916, and passed away on February 24, 2001...

─── iter 3 ───
[memory.read]   1 hit
[perception]    [done] Fetch https://en.wikipedia.org/wiki/Claude_Shannon
                [done] Extract his birth date, death date, and three key contributions to information theory from the fetched content
                [open] Answer the user: Fetch https://en.wikipedia.org/wiki/Claude_Shannon...
[decision]      ANSWER: Claude Shannon was born on April 30, 1916, and passed away on February 24, 2001...

─── iter 4 ───
[memory.read]   1 hit
[perception]    [done] Fetch https://en.wikipedia.org/wiki/Claude_Shannon
                [done] Extract his birth date, death date, and three key contributions to information theory from the fetched content
                [done] Answer the user: Fetch https://en.wikipedia.org/wiki/Claude_Shannon...

[done] all 3 goals satisfied

============================================================
FINAL ANSWER:
============================================================
Claude Shannon was born on April 30, 1916, and passed away on February 24, 2001. As the "father
of information theory," his foundational contributions to the field include:

1.  **Development of Information Entropy:** In his seminal 1948 paper, "A Mathematical Theory of
    Communication," Shannon introduced the concept of information entropy as a measure of the
    uncertainty or information content in a message, which became the fundamental unit of
    measurement in digital communication.
2.  **The Sampling Theorem:** He is credited with the development (and formal proof) of the
    Nyquist–Shannon sampling theorem, which establishes the conditions under which a
    continuous-time signal can be perfectly reconstructed from a sequence of discrete samples.
3.  **Circuit Theory via Boolean Algebra:** In his 1937 master's thesis, Shannon demonstrated
    that electrical relay circuits could be used to solve Boolean algebraic problems, effectively
    mapping logic to electronic hardware and laying the theoretical groundwork for all modern
    digital computer design.
```

---

## Query B — Tokyo Weekend Activities

Clean state. Expected iterations: ~8, limit: 12. **Actual: 6.**

```
$ ./run_query.sh b
State cleared.
Query [b]: Find 3 family-friendly things to do in Tokyo this weekend. Check Saturday's weather forecast there and tell me which one is most appropriate.

─── iter 1 ───
[memory.read]   0 hits
[perception]    [open] Search for family-friendly activities to do in Tokyo this weekend
                [open] Extract 3 family-friendly activities from Tokyo search results
                [open] Search for Tokyo Saturday weather forecast
                [open] Extract Saturday weather details from Tokyo weather search results
                [open] Answer the user: Find 3 family-friendly things to do in Tokyo this weekend...
[decision]      TOOL_CALL: web_search({"query": "family-friendly activities in Tokyo this weekend"})
[action]        → [artifact art:0001, 9254 bytes]

─── iter 2 ───
[memory.read]   1 hit
[perception]    [done] Search for family-friendly activities to do in Tokyo this weekend
                [open] Extract 3 family-friendly activities from Tokyo search results
                [open] Search for Tokyo Saturday weather forecast
                [open] Extract Saturday weather details from Tokyo weather search results
                [open] Answer the user: Find 3 family-friendly things to do in Tokyo this weekend...
[attach]        art:0001 (9254 bytes)
[decision]      ANSWER: For a family visiting Tokyo, there are a variety of engaging activities...

─── iter 3 ───
[memory.read]   1 hit
[perception]    [done] Search for family-friendly activities to do in Tokyo this weekend
                [done] Extract 3 family-friendly activities from Tokyo search results
                [open] Search for Tokyo Saturday weather forecast
                [open] Extract Saturday weather details from Tokyo weather search results
                [open] Answer the user: Find 3 family-friendly things to do in Tokyo this weekend...
[decision]      TOOL_CALL: web_search({"query": "Tokyo weather forecast Saturday"})
[action]        → [artifact art:0002, 9889 bytes]

─── iter 4 ───
[memory.read]   2 hits
[perception]    [done] Search for family-friendly activities to do in Tokyo this weekend
                [done] Extract 3 family-friendly activities from Tokyo search results
                [done] Search for Tokyo Saturday weather forecast
                [open] Extract Saturday weather details from Tokyo weather search results
                [open] Answer the user: Find 3 family-friendly things to do in Tokyo this weekend...
[attach]        art:0002 (9889 bytes)
[decision]      ANSWER: According to the latest weather forecast for Saturday, May 23, 2026,
                Tokyo is expected to be cloudy with a comfortable high of 20°C...

─── iter 5 ───
[memory.read]   2 hits
[perception]    [done] Search for family-friendly activities to do in Tokyo this weekend
                [done] Extract 3 family-friendly activities from Tokyo search results
                [done] Search for Tokyo Saturday weather forecast
                [done] Extract Saturday weather details from Tokyo weather search results
                [open] Answer the user: Find 3 family-friendly things to do in Tokyo this weekend...
[decision]      ANSWER: For a family-friendly weekend in Tokyo, three excellent options include...

─── iter 6 ───
[memory.read]   2 hits
[perception]    [done] Search for family-friendly activities to do in Tokyo this weekend
                [done] Extract 3 family-friendly activities from Tokyo search results
                [done] Search for Tokyo Saturday weather forecast
                [done] Extract Saturday weather details from Tokyo weather search results
                [done] Answer the user: Find 3 family-friendly things to do in Tokyo this weekend...

[done] all 5 goals satisfied

============================================================
FINAL ANSWER:
============================================================
For a family-friendly weekend in Tokyo, three excellent options include:

1.  **Samurai Ninja Museum (Asakusa):** This offers an interactive experience where families can
    participate in kid-friendly ninja training, making it an engaging way to learn about Japanese
    history.
2.  **Ramen-Making Classes (Shibuya):** A fun, hands-on culinary activity suitable for all ages,
    allowing family members to work together to create their own custom ramen.
3.  **Sumo Workshop:** A unique cultural immersion where families can learn about the sport of
    sumo wrestling in an accessible and often humorous setting.

Given the weather forecast for Saturday, May 23, 2026, which predicts a cloudy day with a
comfortable high of 20°C and a very low (10%) chance of precipitation, all three activities are
highly appropriate. However, the **Samurai Ninja Museum** is arguably the most suitable choice,
as it is an indoor activity that provides a perfect escape if the clouds lead to unexpected light
drizzles, while still being centrally located and highly interactive for children.
```

---

## Query C — Mom's Birthday (Durable Memory)

Run 1 and Run 2 use the same `state/`. Expected iterations: 4 / 2.

### Run 1

```
$ ./run_query.sh c1
State cleared.
Query [c1]: My mom's birthday is 15 May 2026. Remember that and give me a calendar reminder for two weeks before and on the day.

─── iter 1 ───
[memory.read]   1 hit
[perception]    [open] Set a calendar reminder for 1 May 2026 for mom's birthday
                [open] Set a calendar reminder for 15 May 2026 for mom's birthday
                [open] Answer the user: My mom's birthday is 15 May 2026...
[decision]      TOOL_CALL: create_file({"content": "Reminder: Mom's birthday is May 15th. Reminder set for May 1st to prepare for the upcoming birthday.", "path": "2026-05-01.txt"})
[action]        → {"ok": true, "path": "2026-05-01.txt", "size_bytes": 100}

─── iter 2 ───
[memory.read]   2 hits
[perception]    [done] Set a calendar reminder for 1 May 2026 for mom's birthday
                [open] Set a calendar reminder for 15 May 2026 for mom's birthday
                [open] Answer the user: My mom's birthday is 15 May 2026...
[decision]      TOOL_CALL: create_file({"path": "2026-05-15.txt", "content": "Reminder: Mom's birthday is May 15th. Reminder set for May 15th, 2026."})
[action]        → {"ok": true, "path": "2026-05-15.txt", "size_bytes": 70}

─── iter 3 ───
[memory.read]   3 hits
[perception]    [done] Set a calendar reminder for 1 May 2026 for mom's birthday
                [done] Set a calendar reminder for 15 May 2026 for mom's birthday
                [open] Answer the user: My mom's birthday is 15 May 2026...
[decision]      ANSWER: I have successfully scheduled the reminders for your mother's birthday...

─── iter 4 ───
[memory.read]   3 hits
[perception]    [done] Set a calendar reminder for 1 May 2026 for mom's birthday
                [done] Set a calendar reminder for 15 May 2026 for mom's birthday
                [done] Answer the user: My mom's birthday is 15 May 2026...

[done] all 3 goals satisfied

============================================================
FINAL ANSWER:
============================================================
I have successfully scheduled the reminders for your mother's birthday. A reminder has been
created for May 1st, 2026, to give you two weeks of notice, and a second reminder is set for
May 15th, 2026, to mark the day of the birthday itself. Both reminder files have been saved in
the system, ensuring you are prepared for the occasion.
```

### Run 2 (same state/, no reset)

```
$ ./run_query.sh c2 --no-clear
Query [c2]: When is mom's birthday?

─── iter 1 ───
[memory.read]   3 hits
[perception]    [open] Answer the user: When is mom's birthday?
[decision]      ANSWER: Mom's birthday is on May 15, 2026...

─── iter 2 ───
[memory.read]   3 hits
[perception]    [done] Answer the user: When is mom's birthday?

[done] all 1 goal satisfied

============================================================
FINAL ANSWER:
============================================================
Mom's birthday is on May 15, 2026. This date has been confirmed and documented in your system
records. Reminder files have also been created in the sandbox for both May 1st and May 15th to
ensure you are prepared for the occasion.
```

---

## Query D — asyncio Synthesis (Pattern B)

Clean state. Expected iterations: ~10, limit: 14. **Actual: 11.**

```
$ ./run_query.sh d
State cleared.
Query [d]: Search for 'Python asyncio best practices', read the top 3 results, and give me a short numbered list of the advice they agree on.

─── iter 1 ───
[memory.read]   0 hits
[perception]    [open] Search for 'Python asyncio best practices'
                [open] List the top 3 URLs from the search results
                [open] Fetch the 1st search result
                [open] Extract key points from the 1st result
                [open] Fetch the 2nd search result
                [open] Extract key points from the 2nd result
                [open] Fetch the 3rd search result
                [open] Extract key points from the 3rd result
                [open] Answer the user: Search for 'Python asyncio best practices'...
[decision]      TOOL_CALL: web_search({"query": "Python asyncio best practices"})
[action]        → [artifact art:0001, 10785 bytes]

─── iter 2 ───
[memory.read]   1 hit
[perception]    [done] Search for 'Python asyncio best practices'
                [open] List the top 3 URLs from the search results
                ... (8 goals open)
[attach]        art:0001 (10785 bytes)
[decision]      ANSWER: The top 3 URLs from the search results are:
                1. https://www.shanechang.com/p/python-asyncio-best-practices-pitfalls
                2. https://discuss.python.org/t/asyncio-best-practices/12576
                3. https://oneuptime.com/blog/post/2026-01-24-asyncio-concurrent-programming-python/view

─── iter 3 ───
[memory.read]   1 hit
[perception]    [done] Search for 'Python asyncio best practices'
                [done] List the top 3 URLs from the search results
                [open] Fetch the 1st search result
                ... (7 goals open)
[attach]        art:0001 (10785 bytes)
[decision]      TOOL_CALL: fetch_url({"url": "https://www.shanechang.com/p/python-asyncio-best-practices-pitfalls"})
[action]        → [artifact art:0002, 8818 bytes]

─── iter 4 ───
[memory.read]   2 hits
[perception]    [done] Fetch the 1st search result
                [open] Extract key points from the 1st result
                ... (6 goals open)
[attach]        art:0002 (8818 bytes)
[decision]      ANSWER: Key points from article 1 (shanechang.com): use asyncio.run() as entry
                point; never block the event loop; use create_task() for concurrency...

─── iter 5 ───
[memory.read]   2 hits
[perception]    [done] Extract key points from the 1st result
                [open] Fetch the 2nd search result
                ... (5 goals open)
[attach]        art:0001 (10785 bytes)
[decision]      TOOL_CALL: fetch_url({"url": "https://discuss.python.org/t/asyncio-best-practices/12576"})
[action]        → [artifact art:0003, 6749 bytes]

─── iter 6 ───
[memory.read]   3 hits
[perception]    [done] Fetch the 2nd search result
                [open] Extract key points from the 2nd result
                ... (4 goals open)
[attach]        art:0003 (6749 bytes)
[decision]      ANSWER: Key points from article 2 (discuss.python.org): understand event loop
                lifecycle; prefer structured concurrency patterns...

─── iter 7 ───
[memory.read]   3 hits
[perception]    [done] Extract key points from the 2nd result
                [open] Fetch the 3rd search result
                ... (3 goals open)
[attach]        art:0001 (10785 bytes)
[decision]      TOOL_CALL: fetch_url({"url": "https://oneuptime.com/blog/post/2026-01-24-asyncio-concurrent-programming-python/view"})
[action]        → [artifact art:0004, 35399 bytes]

─── iter 8 ───
[memory.read]   4 hits
[perception]    [done] Fetch the 3rd search result
                [open] Extract key points from the 3rd result
                ... (2 goals open)
[attach]        art:0004 (35399 bytes)
[decision]      ANSWER: Key points from article 3 (oneuptime.com): do not block event loop;
                use asyncio.gather() for parallel tasks; handle CancelledError...

─── iter 9 ───
[memory.read]   4 hits
[perception]    [done] Extract key points from the 3rd result
                [open] Answer the user: Search for 'Python asyncio best practices'...
[decision]      ANSWER: Based on the analysis of the top three resources...

─── iter 10 ───
[memory.read]   4 hits
[perception]    [done] Answer the user: Search for 'Python asyncio best practices'...

[done] all 9 goals satisfied

============================================================
FINAL ANSWER:
============================================================
Based on the analysis of the top three resources regarding Python's asyncio library, the
following best practices are consistently recommended:

1. Do Not Block the Event Loop: Never use blocking synchronous code (time.sleep(), standard
   requests, or CPU-bound computations) inside an async function — it halts the entire event
   loop and prevents other tasks from progressing.
2. Use asyncio.run() as the Entry Point: Handles creation and destruction of the event loop
   automatically, ensures proper task cleanup, and correctly manages signals.
3. Use High-Level APIs for Concurrency: Use asyncio.gather() or asyncio.TaskGroup rather than
   manually managing tasks. These tools run multiple coroutines concurrently and handle error
   propagation if one task fails.
```

---

## Architecture

| Module | Role | LLM calls |
|---|---|---|
| `memory.py` | Typed KV store; keyword search for retrieval | Only on `remember()` |
| `perception.py` | Decomposes query into goals, marks done | Every iteration (Gemini, temp=1.0) |
| `decision.py` | Returns tool_call or answer for one goal | Every iteration (auto_route=decision) |
| `action.py` | MCP dispatch; large results → ArtifactStore | Never |

State: `state/memory.json` and `state/artifacts/` (gitignored).

---

## Prompt Evaluations

Evaluated against `queries/eval_prompt.md` criteria.

### Perception Prompt (`prompts/perception.txt`)

```json
{
  "explicit_reasoning": true,
  "structured_output": true,
  "tool_separation": true,
  "conversation_loop": true,
  "instructional_framing": true,
  "internal_self_checks": true,
  "reasoning_type_awareness": false,
  "fallbacks": false,
  "overall_clarity": "Highly robust. Pre-output reasoning trace (trace history → apply done rules → verify sticky-done) enforces structured thinking. JSON-only output with explicit schema eliminates format drift. Pattern A/B decomposition and done-marking table are precise. Gaps: no explicit reasoning-type tagging per goal (search vs extraction vs synthesis), and the only fallback for ambiguity is 'set done=false' — no protocol for unresolvable goal state. Adding explicit uncertainty handling and goal-type labels would improve downstream Decision performance."
}
```

### Decision Prompt (`prompts/decision.txt`)

```json
{
  "explicit_reasoning": true,
  "structured_output": true,
  "tool_separation": true,
  "conversation_loop": true,
  "instructional_framing": true,
  "internal_self_checks": true,
  "reasoning_type_awareness": true,
  "fallbacks": true,
  "overall_clarity": "Excellent on all criteria. Step 2 explicitly asks the model to identify reasoning type (factual-lookup | real-time-data | computation | file-operation | synthesis). Step 8 self-check verifies RULE 1 and artifact-handle constraints before output. Step 9 fallback handles tool errors with retry-or-partial-answer logic. Goal-type overrides (RULE 0/0b/0c) prevent the most common failure modes. Minor gap: reasoning trace is internal (used for decision) but not emitted — adding a visible scratchpad field would increase transparency for debugging."
}
```
