from __future__ import annotations
import asyncio
import json
import logging
import sys
import uuid
from typing import Any

logging.basicConfig(
    level=logging.WARNING,
    format="%(name)s %(levelname)s %(message)s",
)

import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

import action as action_mod
from artifacts import ArtifactStore
from memory import Memory
import perception
import decision
from schemas import Goal, ToolCall

MAX_ITERATIONS = 15
_ANALYSIS_KEYWORDS = {
    "extract", "identify", "analyze", "analyse", "summarize", "summarise",
    "synthesize", "synthesise", "compare", "from the retrieved",
    "from the fetched", "from the content", "from retrieved", "from fetched",
    "from the page", "from the article", "from the result",
    "from the 1st result", "from the 2nd result", "from the 3rd result",
    "from the search", "from search",
    "list the top", "list top",
    "determine", "decide", "recommend", "choose", "select",
    "most appropriate", "based on the", "which activity", "which option",
}
_AUTO_ATTACH = True
_FETCH_NTH_KEYWORDS = {
    "fetch the 1st search result", "fetch the 2nd search result",
    "fetch the 3rd search result", "fetch the 4th search result",
    "fetch the 5th search result",
}
_GATEWAY_URL = "http://localhost:8101"


def ensure_gateway() -> None:
    try:
        r = httpx.get(f"{_GATEWAY_URL}/v1/capabilities", timeout=5)
        r.raise_for_status()
    except Exception as e:
        print(f"ERROR: LLM Gateway not reachable at {_GATEWAY_URL}: {e}")
        sys.exit(1)


def mcp_tools_for_decision(tools: list[Any]) -> list[dict]:
    """Convert MCP tool objects to flat gateway tool dicts."""
    result = []
    for t in tools:
        params = {}
        if hasattr(t, "inputSchema") and t.inputSchema:
            schema = t.inputSchema
            if hasattr(schema, "model_dump"):
                params = schema.model_dump()
            elif isinstance(schema, dict):
                params = schema
        result.append({
            "name": t.name,
            "description": getattr(t, "description", "") or "",
            "parameters": params,
        })
    return result


def final_answer_from(history: list[dict]) -> str:
    answers = [h["text"] for h in history if h.get("kind") == "answer" and h.get("text")]
    return answers[-1] if answers else "No answer produced."


async def run(query: str) -> str:
    ensure_gateway()

    mem = Memory()
    artifacts = ArtifactStore()

    # Share artifact store with action module
    action_mod._store = artifacts

    run_id = str(uuid.uuid4())[:8]

    server_params = StdioServerParameters(
        command="uv",
        args=["run", "python", "mcp_server.py"],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            mcp_tool_list = (await session.list_tools()).tools
            tools = mcp_tools_for_decision(mcp_tool_list)

            # Classify and remember the query
            mem.remember(query, source="user", run_id=run_id)

            history: list[dict] = []
            prior_goals: list[Goal] = []

            for iteration in range(MAX_ITERATIONS):
                hits = mem.read(query, history)

                print(f"\n─── iter {iteration+1} ───")
                print(f"[memory.read]   {len(hits)} hit{'s' if len(hits) != 1 else ''}")

                obs = perception.observe(
                    query=query,
                    hits=hits,
                    history=history,
                    prior_goals=prior_goals,
                    run_id=run_id,
                )
                prior_goals = obs.goals

                perc_prefix = "[perception]    "
                perc_indent = " " * len(perc_prefix)
                for i, g in enumerate(obs.goals):
                    status = "[done]" if g.done else "[open]"
                    line_prefix = perc_prefix if i == 0 else perc_indent
                    print(f"{line_prefix}{status} {g.text}")
                    if g.attach_artifact_id:
                        print(f"{perc_indent}  attach={g.attach_artifact_id}")

                if obs.all_done:
                    n = len(obs.goals)
                    print(f"\n[done] all {n} goal{'s' if n != 1 else ''} satisfied")
                    break

                goal = obs.next_unfinished()
                if goal is None:
                    break

                attach_id = goal.attach_artifact_id
                if not attach_id and _AUTO_ATTACH:
                    goal_lower = goal.text.lower()
                    if any(kw in goal_lower for kw in _FETCH_NTH_KEYWORDS):
                        # Attach search artifact so Decision can see URLs to fetch
                        for h in reversed(history):
                            if h.get("kind") == "action" and h.get("art_id") and h.get("tool") == "web_search" and artifacts.exists(h["art_id"]):
                                attach_id = h["art_id"]
                                break
                    elif any(kw in goal_lower for kw in _ANALYSIS_KEYWORDS):
                        for h in reversed(history):
                            if h.get("kind") == "action" and h.get("art_id") and artifacts.exists(h["art_id"]):
                                attach_id = h["art_id"]
                                break

                attached: list[bytes] = []
                if attach_id and artifacts.exists(attach_id):
                    blob = artifacts.get_bytes(attach_id)
                    attached.append(blob)
                    print(f"[attach]        {attach_id} ({len(blob)} bytes)")

                out = decision.next_step(
                    goal=goal,
                    hits=hits,
                    attached=attached,
                    history=history,
                    mcp_tools=tools,
                )

                if out.is_answer:
                    print(f"[decision]      ANSWER: {out.answer[:200]}")
                    history.append({
                        "kind": "answer",
                        "goal_id": goal.id,
                        "goal_text": goal.text,
                        "text": out.answer,
                    })
                else:
                    tc = out.tool_call
                    print(f"[decision]      TOOL_CALL: {tc.name}({json.dumps(tc.arguments)})")
                    result_text, art_id = await action_mod.execute(session, tc)
                    print(f"[action]        → {result_text[:200]}")
                    mem.record_outcome(tc, result_text, art_id, run_id, goal.id)
                    history.append({
                        "kind": "action",
                        "goal_id": goal.id,
                        "goal_text": goal.text,
                        "tool": tc.name,
                        "args": tc.arguments,
                        "result": result_text,
                        "art_id": art_id,
                    })
            else:
                print(f"\n[MAX_ITERATIONS={MAX_ITERATIONS} reached]")

    return final_answer_from(history)


def main():
    if len(sys.argv) < 2:
        print("Usage: python agent.py \"your query here\"")
        sys.exit(1)
    query = sys.argv[1]
    answer = asyncio.run(run(query))
    print("\n" + "="*60)
    print("FINAL ANSWER:")
    print("="*60)
    print(answer)


if __name__ == "__main__":
    main()
