from __future__ import annotations
import uuid
from pathlib import Path

from client import LLM
from schemas import (
    Goal, Observation, MemoryItem,
    PerceptionResponse, PerceivedGoal,
)

_PROMPT = (Path(__file__).parent / "prompts" / "perception.txt").read_text()
_llm = LLM()


def _format_hits(hits: list[MemoryItem]) -> str:
    if not hits:
        return "No relevant memory hits."
    lines = []
    for i, h in enumerate(hits):
        if h.artifact_id:
            artifact_note = f" [artifact: {h.artifact_id} — full content available for attachment]"
        else:
            artifact_note = ""
        lines.append(f"[{i}] ({h.kind}) {h.descriptor}: {h.value}{artifact_note}")
    return "\n".join(lines)


def _format_history(history: list[dict]) -> str:
    if not history:
        return "No history yet."
    lines = []
    for h in history:
        kind = h.get("kind", "unknown")
        if kind == "action":
            lines.append(f"ACTION: {h.get('tool')}({h.get('args', {})}) → {h.get('result', '')[:300]}")
        elif kind == "answer":
            lines.append(f"ANSWER for goal '{h.get('goal_text', '')}': {h.get('text', '')[:300]}")
        else:
            lines.append(f"{kind.upper()}: {str(h)[:200]}")
    return "\n".join(lines)


def _format_prior_goals(goals: list[Goal]) -> str:
    if not goals:
        return "No prior goals."
    lines = []
    for i, g in enumerate(goals):
        status = "DONE" if g.done else "TODO"
        attach = f" [attach: {g.attach_artifact_id}]" if g.attach_artifact_id else ""
        lines.append(f"[{i}] [{status}] {g.text}{attach}")
    return "\n".join(lines)


def observe(
    query: str,
    hits: list[MemoryItem],
    history: list[dict],
    prior_goals: list[Goal],
    run_id: str,
) -> Observation:
    prompt = f"""{_PROMPT}

---

USER QUERY: {query}

MEMORY HITS (indexed 0..{len(hits)-1}):
{_format_hits(hits)}

CONVERSATION HISTORY:
{_format_history(history)}

PRIOR GOALS (preserve order and IDs):
{_format_prior_goals(prior_goals)}

Now produce the updated goal list as JSON.
"""

    schema = PerceptionResponse.model_json_schema()
    resp = _llm.chat(
        prompt=prompt,
        provider="g",
        temperature=1.0,
        response_format={"type": "json_schema", "schema": schema},
        max_tokens=1024,
    )

    parsed = resp.get("parsed")
    if parsed and isinstance(parsed, dict):
        pr = PerceptionResponse(**parsed)
    else:
        import json
        text = resp.get("text", "")
        try:
            pr = PerceptionResponse(**json.loads(text))
        except Exception:
            # fallback: single goal from query
            pr = PerceptionResponse(goals=[PerceivedGoal(text=query, done=False)])

    # Build stable id map from prior goals (by position)
    prior_ids = [g.id for g in prior_goals]

    goals: list[Goal] = []
    for i, pg in enumerate(pr.goals):
        # Reuse positional id from prior run or mint new
        if i < len(prior_ids):
            goal_id = prior_ids[i]
        else:
            goal_id = str(uuid.uuid4())

        # Sticky-done: if prior goal at this position was done, keep it done
        if i < len(prior_goals) and prior_goals[i].done:
            done = True
        elif not history:
            # No history yet — nothing can be done
            done = False
        else:
            done = pg.done

        # Resolve artifact_index → actual art: handle from hits
        attach_id: str | None = None
        if pg.artifact_index is not None:
            idx = pg.artifact_index
            if 0 <= idx < len(hits):
                attach_id = hits[idx].artifact_id  # may be None if hit has no artifact

        goals.append(Goal(
            id=goal_id,
            text=pg.text,
            done=done,
            attach_artifact_id=attach_id,
        ))

    # Force-attach: if any new goal references artifact from history but perception missed it
    # (synthesis goal gets attachment from last artifact-producing action)
    last_art_id: str | None = None
    for h in history:
        if h.get("kind") == "action" and h.get("art_id"):
            last_art_id = h["art_id"]

    return Observation(goals=goals)
