# Session 6 Agent — Multi-Role Cognitive Agent

A multi-role cognitive agent built with four typed modules: `memory.py`, `perception.py`, `decision.py`, and `action.py`, wired together in `agent6.py`. All LLM calls go through the LLM Gateway V3 (`localhost:8101`). Tool dispatch uses MCP stdio transport.

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

Actual queries are in `docs/query_<id>.txt`. `run_query.sh` resets state automatically unless `--no-clear` is passed.

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
                [open] Extract Claude Shannon's birth date, death date, and three key contributions to information theory from the retrieved content
                [open] Answer the user: Fetch https://en.wikipedia.org/wiki/Claude_Shannon and tell me his birth date, death date, and three key contributions to information theory.
[decision]      TOOL_CALL: fetch_url({"url": "https://en.wikipedia.org/wiki/Claude_Shannon"})
[action]        → [artifact art:0001, 266693 bytes]

─── iter 2 ───
[memory.read]   1 hit
[perception]    [done] Fetch https://en.wikipedia.org/wiki/Claude_Shannon
                [open] Extract Claude Shannon's birth date, death date, and three key contributions to information theory from the retrieved content
                [open] Answer the user: Fetch https://en.wikipedia.org/wiki/Claude_Shannon...
[attach]        art:0001 (266693 bytes)
[decision]      ANSWER: Claude Shannon was born on April 30, 1916, and he passed away on February 24, 2001...

─── iter 3 ───
[memory.read]   1 hit
[perception]    [done] Fetch https://en.wikipedia.org/wiki/Claude_Shannon
                [done] Extract Claude Shannon's birth date, death date, and three key contributions to information theory from the retrieved content
                [open] Answer the user: Fetch https://en.wikipedia.org/wiki/Claude_Shannon...
[decision]      ANSWER: Claude Shannon was born on April 30, 1916, and passed away on February 24, 2001...

─── iter 4 ───
[memory.read]   1 hit
[perception]    [done] Fetch https://en.wikipedia.org/wiki/Claude_Shannon
                [done] Extract Claude Shannon's birth date, death date, and three key contributions to information theory from the retrieved content
                [done] Answer the user: Fetch https://en.wikipedia.org/wiki/Claude_Shannon...

[done] all 3 goals satisfied

============================================================
FINAL ANSWER:
============================================================
Claude Shannon was born on April 30, 1916, and passed away on February 24, 2001. Widely
recognized as the "father of information theory," his seminal work includes the introduction of
information entropy as a measure of information content, which provides a mathematical framework
for data compression and transmission. Additionally, he established the fundamental connection
between Boolean algebra and electronic circuits, which serves as the theoretical basis for modern
digital computing. Finally, he formulated the Shannon-Hartley theorem, which defines the maximum
rate at which information can be reliably transmitted over a communications channel with a
specified bandwidth in the presence of noise.
```

---

## Query B — Tokyo Weekend Activities

Clean state. Expected iterations: ~8, limit: 12. **Actual: 8.**

```
$ ./run_query.sh b
State cleared.
Query [b]: Find 3 family-friendly things to do in Tokyo this weekend. Check Saturday's weather forecast there and tell me which one is most appropriate.

─── iter 1 ───
[memory.read]   0 hits
[perception]    [open] Search for family-friendly activities in Tokyo this weekend
                [open] Extract 3 family-friendly activities from search results
                [open] Search for Tokyo weather forecast for Saturday
                [open] Extract Saturday weather details from weather search results
                [open] Identify which of the 3 activities is most appropriate for the Saturday weather
                [open] Answer the user: Find 3 family-friendly things to do in Tokyo this weekend...
[decision]      TOOL_CALL: web_search({"query": "family-friendly activities in Tokyo this weekend"})
[action]        → [artifact art:0001, 11475 bytes]

─── iter 2 ───
[memory.read]   1 hit
[perception]    [done] Search for family-friendly activities in Tokyo this weekend
                [open] Extract 3 family-friendly activities from search results
                [open] Search for Tokyo weather forecast for Saturday
                [open] Extract Saturday weather details from weather search results
                [open] Identify which of the 3 activities is most appropriate for the Saturday weather
                [open] Answer the user: Find 3 family-friendly things to do in Tokyo this weekend...
[attach]        art:0001 (11475 bytes)
[decision]      ANSWER: Tokyo offers a wide variety of family-friendly activities...

─── iter 3 ───
[memory.read]   1 hit
[perception]    [done] Search for family-friendly activities in Tokyo this weekend
                [done] Extract 3 family-friendly activities from search results
                [open] Search for Tokyo weather forecast for Saturday
                [open] Extract Saturday weather details from weather search results
                [open] Identify which of the 3 activities is most appropriate for the Saturday weather
                [open] Answer the user: Find 3 family-friendly things to do in Tokyo this weekend...
[decision]      TOOL_CALL: web_search({"query": "Tokyo weather forecast Saturday"})
[action]        → [artifact art:0002, 10473 bytes]

─── iter 4 ───
[memory.read]   2 hits
[perception]    [done] Search for family-friendly activities in Tokyo this weekend
                [done] Extract 3 family-friendly activities from search results
                [done] Search for Tokyo weather forecast for Saturday
                [open] Extract Saturday weather details from weather search results
                [open] Identify which of the 3 activities is most appropriate for the Saturday weather
                [open] Answer the user: Find 3 family-friendly things to do in Tokyo this weekend...
[attach]        art:0002 (10473 bytes)
[decision]      ANSWER: Based on the provided weather forecasts for Tokyo in May 2026...

─── iter 5 ───
[memory.read]   2 hits
[perception]    [done] Search for family-friendly activities in Tokyo this weekend
                [done] Extract 3 family-friendly activities from search results
                [done] Search for Tokyo weather forecast for Saturday
                [done] Extract Saturday weather details from weather search results
                [open] Identify which of the 3 activities is most appropriate for the Saturday weather
                [open] Answer the user: Find 3 family-friendly things to do in Tokyo this weekend...
[attach]        art:0002 (10473 bytes)
[decision]      ANSWER: Given that the weather forecast for Saturday, May 23, 2026, in Tokyo predicts sunny, pleasant conditions...

─── iter 6 ───
[memory.read]   2 hits
[perception]    [done] Search for family-friendly activities in Tokyo this weekend
                [done] Extract 3 family-friendly activities from search results
                [done] Search for Tokyo weather forecast for Saturday
                [done] Extract Saturday weather details from weather search results
                [done] Identify which of the 3 activities is most appropriate for the Saturday weather
                [open] Answer the user: Find 3 family-friendly things to do in Tokyo this weekend...
[attach]        art:0002 (10473 bytes)
[decision]      TOOL_CALL: web_search({"query": "family-friendly activities in Tokyo for a sunny day"})
[action]        → [artifact art:0003, 10383 bytes]

─── iter 7 ───
[memory.read]   3 hits
[perception]    [done] Search for family-friendly activities in Tokyo this weekend
                [done] Extract 3 family-friendly activities from search results
                [done] Search for Tokyo weather forecast for Saturday
                [done] Extract Saturday weather details from weather search results
                [done] Identify which of the 3 activities is most appropriate for the Saturday weather
                [open] Answer the user: Find 3 family-friendly things to do in Tokyo this weekend...
[attach]        art:0003 (10383 bytes)
[decision]      ANSWER: For your weekend in Tokyo, here are three excellent family-friendly activities...

─── iter 8 ───
[memory.read]   3 hits
[perception]    [done] Search for family-friendly activities in Tokyo this weekend
                [done] Extract 3 family-friendly activities from search results
                [done] Search for Tokyo weather forecast for Saturday
                [done] Extract Saturday weather details from weather search results
                [done] Identify which of the 3 activities is most appropriate for the Saturday weather
                [done] Answer the user: Find 3 family-friendly things to do in Tokyo this weekend...

[done] all 6 goals satisfied

============================================================
FINAL ANSWER:
============================================================
For your weekend in Tokyo, here are three excellent family-friendly activities:

1. Ghibli Museum (Mitaka): This enchanting museum allows children to explore the whimsical world
   of Studio Ghibli, featuring a giant Cat Bus and short films. It is located within Inokashira
   Park, which provides beautiful walking paths and outdoor space.
2. Sunshine City (Ikebukuro): This massive entertainment complex is a one-stop destination for
   families. It houses the Sunshine Aquarium, the Tenbou-Park observation deck, and the Pokemon
   Center MEGA TOKYO.
3. Ueno Zoo: As Japan's oldest zoo, home to over 300 animal species including giant pandas.

Given the favorable weather forecast for Saturday, May 23 (sunny, high of 24°C, no precipitation),
the Ghibli Museum is the most appropriate choice. Situated inside Inokashira Park, the sunny
weather allows families to enjoy both the indoor museum exhibits and the surrounding park grounds.
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
[perception]    [open] Set a calendar reminder for 1 May 2026
                [open] Set a calendar reminder for 15 May 2026
                [open] Answer the user: My mom's birthday is 15 May 2026...
[decision]      TOOL_CALL: create_file({"content": "Reminder: Calendar event set for 1 May 2026.", "path": "2026-05-01.txt"})
[action]        → {"ok": true, "path": "2026-05-01.txt", "size_bytes": 44}

─── iter 2 ───
[memory.read]   2 hits
[perception]    [done] Set a calendar reminder for 1 May 2026
                [open] Set a calendar reminder for 15 May 2026
                [open] Answer the user: My mom's birthday is 15 May 2026...
[decision]      TOOL_CALL: create_file({"content": "Reminder: Mom's birthday is on 15 May 2026.", "path": "2026-05-15.txt"})
[action]        → {"ok": true, "path": "2026-05-15.txt", "size_bytes": 43}

─── iter 3 ───
[memory.read]   3 hits
[perception]    [done] Set a calendar reminder for 1 May 2026
                [done] Set a calendar reminder for 15 May 2026
                [open] Answer the user: My mom's birthday is 15 May 2026...
[decision]      ANSWER: I have successfully set the requested reminders for your mother's birthday...

─── iter 4 ───
[memory.read]   3 hits
[perception]    [done] Set a calendar reminder for 1 May 2026
                [done] Set a calendar reminder for 15 May 2026
                [done] Answer the user: My mom's birthday is 15 May 2026...

[done] all 3 goals satisfied

============================================================
FINAL ANSWER:
============================================================
I have successfully set the requested reminders for your mother's birthday. A reminder file has
been created for the actual day, May 15, 2026, and a second reminder file has been created for
two weeks prior, on May 1, 2026. You can rest assured that both dates are now documented in the
system to help you prepare for the celebration.
```

### Run 2 (same state/, no reset)

```
$ ./run_query.sh c2 --no-clear
Query [c2]: When is mom's birthday?

─── iter 1 ───
[memory.read]   2 hits
[perception]    [open] Answer the user: When is mom's birthday?
[decision]      ANSWER: Mom's birthday is on May 15, 2026...

─── iter 2 ───
[memory.read]   3 hits
[perception]    [done] Answer the user: When is mom's birthday?

[done] all 1 goal satisfied

============================================================
FINAL ANSWER:
============================================================
Mom's birthday is on May 15, 2026. This information is confirmed by the records stored in your
memory. Additionally, a reminder file has been created in the system to ensure this date is
noted for the future.
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
                [open] Synthesise the common advice from fetched pages
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
                [open] Synthesise the common advice from fetched pages
                [open] Answer the user: Search for 'Python asyncio best practices'...
[decision]      ANSWER: Common advice across all 3 sources: (1) never block event loop,
                (2) use asyncio.run() as entry point, (3) use gather()/create_task()...

─── iter 10 ───
[memory.read]   4 hits
[perception]    [done] Synthesise the common advice from fetched pages
                [open] Answer the user: Search for 'Python asyncio best practices'...
[decision]      ANSWER: Based on the analysis of the top three resources...

─── iter 11 ───
[memory.read]   4 hits
[perception]    [done] Answer the user: Search for 'Python asyncio best practices'...

[done] all 10 goals satisfied

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
  "fallbacks": true,
  "overall_clarity": "Strong multi-turn structure with JSON schema, worked examples, sticky-done safety rule, and explicit pre-output trace step. Reasoning-type tagging omitted — would require schema change and risk breaking JSON parsing."
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
  "reasoning_type_awareness": false,
  "fallbacks": true,
  "overall_clarity": "Clear numbered decision process with hard rules (RULE 0/0b/1/2/3), self-check against all rules before output, and fallback guidance for tool errors. Step 2 encourages reasoning-type identification but it is internal-only with no output tag or enforcement — criterion not fully satisfied."
}
```
