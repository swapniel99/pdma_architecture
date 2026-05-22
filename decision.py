from __future__ import annotations
import logging
from pathlib import Path
from typing import Any

from client import LLM

log = logging.getLogger(__name__)
# log.setLevel(logging.DEBUG)

from schemas import Goal, MemoryItem, DecisionOutput, ToolCall

_PROMPT = (Path(__file__).parent / "prompts" / "decision.txt").read_text()
_llm = LLM()


def _format_hits(hits: list[MemoryItem]) -> str:
    if not hits:
        return "No relevant memory."
    lines = []
    for h in hits:
        lines.append(f"- ({h.kind}) {h.descriptor}: {h.value}")
    return "\n".join(lines)


def _format_history(history: list[dict]) -> str:
    if not history:
        return "No history yet."
    # Track fetched URLs to show explicitly
    fetched_urls: list[str] = []
    for h in history:
        if h.get("kind") == "action" and h.get("tool") == "fetch_url":
            url = h.get("args", {}).get("url", "")
            if url:
                fetched_urls.append(url)

    lines = []
    if fetched_urls:
        lines.append(f"ALREADY FETCHED URLS (do NOT fetch again): {', '.join(fetched_urls)}")

    for h in history:
        kind = h.get("kind", "unknown")
        if kind == "action":
            lines.append(f"TOOL {h.get('tool')} result: {h.get('result', '')[:400]}")
        elif kind == "answer":
            lines.append(f"ANSWER: {h.get('text', '')[:400]}")
    return "\n".join(lines[-12:])


def _format_attached(attached: list[bytes]) -> str:
    if not attached:
        return ""
    parts = []
    for i, blob in enumerate(attached):
        text = blob.decode("utf-8", errors="replace")
        parts.append(f"--- ATTACHMENT {i} ---\n{text}\n--- END ATTACHMENT {i} ---")
    return "\n".join(parts)


def next_step(
    goal: Goal,
    hits: list[MemoryItem],
    attached: list[bytes],
    history: list[dict],
    mcp_tools: list[dict],
) -> DecisionOutput:
    log.debug("goal=%r attached_sizes=%s", goal.text, [len(b) for b in attached])
    attached_section = _format_attached(attached)
    attached_text = f"\nATTACHED ARTIFACTS:\n{attached_section}" if attached_section else ""

    prompt = f"""{_PROMPT}

---

CURRENT GOAL: {goal.text}

MEMORY HITS:
{_format_hits(hits)}

CONVERSATION HISTORY:
{_format_history(history)}
{attached_text}

Decide: call a tool or produce a final answer.
"""

    import time
    for attempt in range(3):
        try:
            resp = _llm.chat(
                prompt=prompt,
                auto_route="decision",
                tools=mcp_tools,
                tool_choice="auto",
                max_tokens=2048,
                temperature=0.7,
            )
            break
        except Exception as e:
            if attempt < 2:
                time.sleep(3)
            else:
                raise

    log.debug("resp_keys=%s has_tool_calls=%s text_preview=%r", list(resp.keys()), bool(resp.get("tool_calls")), resp.get("text", "")[:100])
    tool_calls = resp.get("tool_calls") or []
    if tool_calls:
        first = tool_calls[0]
        name = first.get("name") or first.get("function", {}).get("name", "")
        arguments = first.get("arguments") or first.get("function", {}).get("arguments") or {}
        if isinstance(arguments, str):
            import json
            try:
                arguments = json.loads(arguments)
            except Exception:
                arguments = {}
        return DecisionOutput(tool_call=ToolCall(name=name, arguments=arguments))

    text = resp.get("text", "").strip()
    if not text:
        text = "I was unable to determine a course of action for this goal."
    return DecisionOutput(answer=text)
