"""Module for the agent's Perception cognitive role.

The perception module is responsible for orchestrating task execution by examining the
user's query, memory hits, and execution history to produce and maintain a structured list
of goals (the plan) inside an Observation. It manages goal updates, ensures positional goal
identity (by reusing prior goal IDs), guarantees "sticky-done" goal completions, and
resolves LLM-perceived artifact references into actual store handles.
"""

from __future__ import annotations
import logging
import uuid
from pathlib import Path

from client import LLM

log = logging.getLogger(__name__)
# log.setLevel(logging.DEBUG)

from schemas import (
    Goal, Observation, MemoryItem,
    PerceptionResponse, PerceivedGoal,
)

_PROMPT = (Path(__file__).parent / "prompts" / "perception.txt").read_text()
_llm = LLM()


def _format_hits(hits: list[MemoryItem]) -> str:
    """Formats a list of retrieved memory hits into a readable structured text prompt block.

    Args:
        hits: The list of retrieved MemoryItem records.

    Returns:
        A formatted string detailing the index, category, descriptor, and value
        of each hit, along with indications of any associated artifact IDs.
    """
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
    """Formats the conversation and action execution history into a readable prompt block.

    Args:
        history: The list of execution step dictionaries.

    Returns:
        A formatted text summary of tool actions, tool results (truncated to 300 characters),
        and previous goal answers.
    """
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
    """Formats the prior goals list into a structured status report for the LLM.

    Allows the perception model to review previous progress and carry over
    positional goals.

    Args:
        goals: The list of prior Goal instances from the previous iteration.

    Returns:
        A formatted string outlining the index, status (DONE/TODO), and text of each prior goal.
    """
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
    """Generates the updated set of agent goals by consulting the perception LLM.

    Integrates context, prior goals, and retrieved memory hits into a structured
    prompt. Calls the LLM to yield an updated goal plan, ensuring:
      - Positional goal identity: Prior goal IDs are preserved by index alignment.
      - Sticky-done state: Once a goal is marked done, it cannot be reverted.
      - Artifact resolution: Maps LLM-selected numeric artifact indexes back to actual
        artifact handles (e.g., 'art:NNNN') retrieved from memory hits.

    Args:
        query: The primary user request or objective.
        hits: A list of relevant MemoryItem hits retrieved for this step.
        history: The chronological record of action outcomes and answers.
        prior_goals: The list of Goal items generated in the previous iteration.
        run_id: The unique identifier of the active execution run.

    Returns:
        An Observation instance holding the updated, ordered list of Goal items.
    """
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

    log.debug("hits_section=\n%s", _format_hits(hits))
    log.debug("history_section=\n%s", _format_history(history))

    schema = PerceptionResponse.model_json_schema()
    resp = _llm.chat(
        prompt=prompt,
        provider="g",
        temperature=0.2,
        response_format={"type": "json_schema", "schema": schema},
        max_tokens=1024,
    )

    log.debug("raw_resp=%s", resp)

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
        log.debug("goal[%d] text=%r done=%s artifact_index=%s attach_id=%s", i, pg.text, pg.done, pg.artifact_index, attach_id)

        goals.append(Goal(
            id=goal_id,
            text=pg.text,
            done=done,
            attach_artifact_id=attach_id,
        ))

    return Observation(goals=goals)
