from __future__ import annotations
import asyncio
import sys
import uuid
from typing import Any

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


async def _synthesize_final_answer(query: str, history: list[dict], mem: Memory) -> str:
    """Call LLM to synthesize a final answer from all collected history."""
    from client import LLM
    artifacts = ArtifactStore()
    parts = []
    for h in history:
        if h.get("kind") == "action" and h.get("result"):
            result = h["result"]
            art_id = h.get("art_id")
            if art_id and artifacts.exists(art_id):
                # Load full artifact content (up to 6000 chars)
                content = artifacts.get_bytes(art_id).decode("utf-8", errors="replace")[:6000]
                parts.append(f"Tool {h.get('tool')} full result:\n{content}")
            else:
                parts.append(f"Tool {h.get('tool')} result: {result[:800]}")
        elif h.get("kind") == "answer" and h.get("text"):
            text = h["text"]
            # Skip meta-commentary answers
            meta_patterns = ["Since we already", "I was unable", "based on available information"]
            if not any(text.startswith(p) for p in meta_patterns) and len(text) > 100:
                parts.append(f"Partial answer: {text[:600]}")

    context = "\n\n".join(parts)
    if not context:
        return "No answer produced."

    resp = LLM().chat(
        prompt=(
            f"Based on the research results below, provide a complete, specific answer to: {query}\n\n"
            f"Include all specific facts (dates, names, figures, weather conditions) found in the results. "
            f"Write at least 3 complete sentences.\n\nRESEARCH RESULTS:\n{context}"
        ),
        auto_route="decision",
        max_tokens=1024,
        temperature=0.3,
    )
    return resp.get("text", context)


def final_answer_from(history: list[dict], query: str = "") -> str:
    answers = [h["text"] for h in history if h.get("kind") == "answer" and h.get("text")]
    if answers:
        return answers[-1]
    # fallback: synthesize from tool results
    parts = []
    for h in history:
        if h.get("kind") == "action" and h.get("result"):
            parts.append(f"Tool {h.get('tool')}: {h['result'][:600]}")
    if parts:
        from client import LLM
        context = "\n".join(parts)
        resp = LLM().chat(
            prompt=f"Based on these tool results, answer the query: {query}\n\nResults:\n{context}",
            auto_route="decision",
            max_tokens=1024,
            temperature=0.5,
        )
        return resp.get("text", context)
    return "No answer produced."


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

                obs = perception.observe(
                    query=query,
                    hits=hits,
                    history=history,
                    prior_goals=prior_goals,
                    run_id=run_id,
                )
                prior_goals = obs.goals

                print(f"\n[iter {iteration+1}] Goals:")
                for g in obs.goals:
                    status = "✓" if g.done else "○"
                    attach = f" [attach={g.attach_artifact_id}]" if g.attach_artifact_id else ""
                    print(f"  {status} {g.text}{attach}")

                if obs.all_done:
                    print(f"[iter {iteration+1}] All goals done. Stopping.")
                    break

                goal = obs.next_unfinished()
                if goal is None:
                    break

                # Retrieve attached artifact bytes
                # Auto-attach: if no explicit attachment, use the most recent fetch_url artifact
                attach_id = goal.attach_artifact_id
                if not attach_id:
                    for h in reversed(history):
                        if h.get("kind") == "action" and h.get("art_id") and h.get("tool") == "fetch_url":
                            candidate = h["art_id"]
                            if artifacts.exists(candidate):
                                attach_id = candidate
                                break

                attached: list[bytes] = []
                if attach_id and artifacts.exists(attach_id):
                    attached.append(artifacts.get_bytes(attach_id))

                out = decision.next_step(
                    goal=goal,
                    hits=hits,
                    attached=attached,
                    history=history,
                    mcp_tools=tools,
                )

                if out.is_answer:
                    print(f"[iter {iteration+1}] Answer: {out.answer[:200]}")
                    history.append({
                        "kind": "answer",
                        "goal_id": goal.id,
                        "goal_text": goal.text,
                        "text": out.answer,
                    })
                else:
                    tc = out.tool_call
                    print(f"[iter {iteration+1}] Tool: {tc.name}({list(tc.arguments.keys())})")
                    result_text, art_id = await action_mod.execute(session, tc)
                    print(f"[iter {iteration+1}] Result: {result_text[:150]}")
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
                print(f"[MAX_ITERATIONS={MAX_ITERATIONS} reached]")

    return await _synthesize_final_answer(query, history, mem)


def main():
    if len(sys.argv) < 2:
        print("Usage: python agent6.py \"your query here\"")
        sys.exit(1)
    query = sys.argv[1]
    answer = asyncio.run(run(query))
    print("\n" + "="*60)
    print("FINAL ANSWER:")
    print("="*60)
    print(answer)


if __name__ == "__main__":
    main()
