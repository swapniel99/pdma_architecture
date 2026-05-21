# Session 6 Agent — Multi-Role Cognitive Agent

A multi-role cognitive agent built with four typed modules: `memory.py`, `perception.py`, `decision.py`, and `action.py`, wired together in `agent6.py`. All LLM calls go through the LLM Gateway V3 (`localhost:8101`). Tool dispatch uses MCP stdio transport.

## Prerequisites

- LLM Gateway V3 running at `http://localhost:8101`
- `.env` with `TAVILY_API_KEY`
- `uv` installed

## Run Commands

```bash
# Reset state between runs
rm -rf state/memory.json state/artifacts/

# Query A — Claude Shannon Wikipedia
uv run python agent6.py "Who is Claude Shannon? What are his birth date, death date, and 3 major contributions to information theory?"

# Query B — Tokyo weekend activities
uv run python agent6.py "I'm visiting Tokyo this Saturday. Based on the weather forecast, recommend one activity from: visit Senso-ji temple, attend outdoor summer festival, or have ramen in a cozy shop. Justify your recommendation."

# Query C — Mom's birthday (2 runs, same state/)
uv run python agent6.py "My mom's birthday is on 15 May 2026. Please create a reminder file in the sandbox for it, and also note that she likes chocolate cake."
uv run python agent6.py "When is mom's birthday?"

# Query D — asyncio synthesis
uv run python agent6.py "Find the top asyncio best practices by fetching at least 2 web pages about Python asyncio. Then synthesize a numbered list of the top 5 pieces of advice that appear in multiple sources."
```

---

## Query A — Claude Shannon Wikipedia

Clean state. Expected iterations: 3, limit: 6.

```
$ rm -rf state/memory.json state/artifacts/
$ uv run python agent6.py "Who is Claude Shannon? What are his birth date, death date, and 3 major contributions to information theory?"

[iter 1] Goals:
  ○ Identify who Claude Shannon is
  ○ Find Claude Shannon's birth date
  ○ Find Claude Shannon's death date
  ○ List 3 major contributions of Claude Shannon to information theory
[iter 1] Tool: web_search(['query'])
[iter 1] Result: [artifact art:8db8e1e4b746d087, 8285 bytes] preview: ...

[iter 2] Goals:
  ○ Identify who Claude Shannon is [attach=art:8db8e1e4b746d087]
  ○ Find Claude Shannon's birth date [attach=art:8db8e1e4b746d087]
  ○ Find Claude Shannon's death date [attach=art:8db8e1e4b746d087]
  ○ List 3 major contributions of Claude Shannon to information theory [attach=art:8db8e1e4b746d087]
[iter 2] Answer: Claude Shannon, full name Claude Elwood Shannon, was an American mathematician...

[iter 3] Goals:
  ✓ Identify who Claude Shannon is
  ✓ Find Claude Shannon's birth date
  ○ Find Claude Shannon's death date
  ○ List 3 major contributions of Claude Shannon to information theory
[iter 3] Answer: Claude Shannon died in 2001. Specifically, he passed away...

[iter 4] Goals:
  ✓ Identify who Claude Shannon is
  ✓ Find Claude Shannon's birth date
  ✓ Find Claude Shannon's death date
  ○ List 3 major contributions of Claude Shannon to information theory
[iter 4] Tool: fetch_url(['url'])
[iter 4] Result: [artifact art:db4fbba0dee4ae81, 19363 bytes] preview: ...

[iter 5] Goals:
  ✓ Identify who Claude Shannon is
  ✓ Find Claude Shannon's birth date
  ✓ Find Claude Shannon's death date
  ○ List 3 major contributions of Claude Shannon to information theory
[iter 5] Answer: Claude Shannon made several key contributions...

[iter 6] Goals:
  ✓ Identify who Claude Shannon is
  ✓ Find Claude Shannon's birth date
  ✓ Find Claude Shannon's death date
  ✓ List 3 major contributions of Claude Shannon to information theory
[iter 6] All goals done. Stopping.

============================================================
FINAL ANSWER:
============================================================
Claude Elwood Shannon (April 30, 1916 – February 24, 2001) was an American mathematician and
electrical engineer widely regarded as the father of information theory. Born in Petoskey,
Michigan, he revolutionized digital circuit design by applying Boolean algebra to relay and
switching circuits in his 1937 MIT master's thesis, which laid the groundwork for modern digital
computers. Among his three major contributions to information theory are: (1) the introduction of
the "bit" as the fundamental unit of information, enabling precise quantification of information;
(2) the formulation of Shannon Entropy, a measure of uncertainty or information content analogous
to thermodynamic entropy; and (3) the development of the Shannon Channel Capacity Theorem, which
defines the maximum rate at which information can be reliably transmitted over a communication
channel. These foundational ideas have profoundly influenced communications, computing, biology,
and many other fields.
```

---

## Query B — Tokyo Weekend Activities

Clean state. Expected iterations: ~6, limit: 12.

```
$ rm -rf state/memory.json state/artifacts/
$ uv run python agent6.py "I'm visiting Tokyo this Saturday. Based on the weather forecast, recommend one activity from: visit Senso-ji temple, attend outdoor summer festival, or have ramen in a cozy shop. Justify your recommendation."

[iter 1] Goals:
  ○ Identify the weather forecast for Tokyo this Saturday.
  ○ Recommend one activity from the provided list (Senso-ji temple, summer festival, or ramen shop) based on the weather.
  ○ Justify the recommendation based on the weather forecast.
[iter 1] Tool: web_search(['query', 'max_results'])
[iter 1] Result: [artifact art:004735e25a0567f4, 11560 bytes] preview: ...

[iter 2] Goals:
  ○ Identify the weather forecast for Tokyo this Saturday.
  ○ Recommend one activity from the provided list...
  ○ Justify the recommendation...
[iter 2] Tool: web_search(['query', 'max_results'])
[iter 2] Result: [artifact art:004735e25a0567f4, 11560 bytes] preview: ...

[iter 3] Goals:
  ✓ Identify the weather forecast for Tokyo this Saturday. [attach=art:004735e25a0567f4]
  ✓ Recommend one activity from the provided list...
  ✓ Justify the recommendation...
[iter 3] All goals done. Stopping.

============================================================
FINAL ANSWER:
============================================================
Based on the weather forecast for Tokyo this Saturday, May 2026, I recommend visiting Senso-ji
Temple. The forecast shows daytime temperatures in Tokyo reaching around 22°C (71.6°F) with
nighttime lows of 17°C (62.6°F), and humidity levels averaging 71%, which creates warm but
comfortable conditions ideal for sightseeing. While light rain or muggy conditions after showers
are possible—May averages about 9 rainy days—there is no indication of heavy rain or extreme heat
that would disrupt outdoor plans. An outdoor summer festival might be less enjoyable due to
potential humidity and sporadic showers, while a cozy ramen shop, though appealing, would not take
full advantage of the pleasant daytime warmth; therefore, visiting the historic and culturally rich
Senso-ji Temple in Asakusa offers the best balance of comfort, activity, and weather suitability.
```

---

## Query C — Mom's Birthday (Durable Memory)

Run 1 and Run 2 use the same `state/`. Expected iterations: 4 / 2.

### Run 1

```
$ rm -rf state/memory.json state/artifacts/
$ uv run python agent6.py "My mom's birthday is on 15 May 2026. Please create a reminder file in the sandbox for it, and also note that she likes chocolate cake."

[iter 1] Goals:
  ○ Create a reminder file for Mom's birthday on May 15, 2026, including the preference for chocolate cake.
[iter 1] Tool: create_file(['path', 'content'])
[iter 1] Result: type='text' text='{"ok": true, "path": "moms_birthday_reminder.txt", "size_bytes": 101}'

[iter 2] Goals:
  ✓ Create a reminder file for Mom's birthday on May 15, 2026, including the preference for chocolate cake.
[iter 2] All goals done. Stopping.

============================================================
FINAL ANSWER:
============================================================
Since your mom's birthday is on 15 May 2026, a reminder file named 'moms_birthday_reminder.txt'
has been created in the sandbox. The file notes both the date (May 15, 2026) and her preference for
chocolate cake. With this reminder in place, you can plan ahead to celebrate her birthday with the
chocolate cake she loves.
```

### Run 2 (same state/, no reset)

```
$ uv run python agent6.py "When is mom's birthday?"

[iter 1] Goals:
  ○ Identify the date of mom's birthday from the available memory hits
[iter 1] Answer: The date of mom's birthday is available in the memory hits.

[iter 2] Goals:
  ✓ Identify the date of mom's birthday from the available memory hits
[iter 2] All goals done. Stopping.

============================================================
FINAL ANSWER:
============================================================
Mom's birthday is on May 15, 2026. This date is confirmed by the information stored in the file
named 'moms_birthday_reminder.txt,' which serves as a reminder for the occasion. Additionally, it
is noted that for her birthday celebration, she prefers chocolate cake.
```

---

## Query D — asyncio Synthesis

Clean state. Expected iterations: 5–7, limit: 14.

```
$ rm -rf state/memory.json state/artifacts/
$ uv run python agent6.py "Find the top asyncio best practices by fetching at least 2 web pages about Python asyncio. Then synthesize a numbered list of the top 5 pieces of advice that appear in multiple sources."

[iter 1] Goals:
  ○ Fetch at least 2 web pages about Python asyncio best practices.
  ○ Synthesize a numbered list of the top 5 pieces of asyncio advice from the fetched sources.
[iter 1] Tool: web_search(['query', 'max_results'])
[iter 1] Result: [artifact art:2f0e322505062fa1, 10952 bytes] preview: ...

[iter 2] Goals:
  ○ Fetch at least 2 web pages about Python asyncio best practices.
  ✓ Synthesize a numbered list of the top 5 pieces of asyncio advice from the fetched sources.
[iter 2] Tool: fetch_url(['url'])
[iter 2] Result: [artifact art:a53effa9dcf5c071, 6765 bytes] preview: ...

[iter 3] Goals:
  ○ Fetch at least 2 web pages about Python asyncio best practices.
  ✓ Synthesize a numbered list...
[iter 3] Tool: web_search(['query', 'max_results'])
[iter 3] Result: [artifact art:2f0e322505062fa1, 10952 bytes] preview: ...

[iter 4] Goals:
  ✓ Fetch at least 2 web pages about Python asyncio best practices.
  ✓ Synthesize a numbered list of the top 5 pieces of asyncio advice from the fetched sources.
[iter 4] All goals done. Stopping.

============================================================
FINAL ANSWER:
============================================================
Based on the research results from two primary web sources — Discussions on Python.org and
OneUptime Blog — the following numbered list presents the top 5 asyncio best practices:

1. Never block the event loop with synchronous operations — use `await asyncio.sleep()` instead of
   `time.sleep()` inside async functions.

2. Use `asyncio.create_task()` to run independent operations concurrently rather than awaiting
   coroutines sequentially.

3. Always start asyncio programs with `asyncio.run()` as the standard safe entry point since
   Python 3.7, replacing manual loop management.

4. Run blocking I/O or CPU-bound code in a thread pool using `loop.run_in_executor()` to prevent
   blocking the main event loop.

5. Handle task cancellation gracefully using try/except for `asyncio.CancelledError` to allow
   cleanup before re-raising the exception.
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
