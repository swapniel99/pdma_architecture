"""Module for executing cognitive agent actions via MCP (Model Context Protocol).

This module handles calling tools through the MCP session, sanitizing arguments,
collapsing rich tool outputs into clean text, and redirecting tool outputs that
exceed a size limit to the out-of-band ArtifactStore.
"""

from __future__ import annotations
from typing import Any

from artifacts import ArtifactStore
from schemas import ToolCall

_store = ArtifactStore()
_SIZE_LIMIT = 4096


def _collapse_content(content: Any) -> str:
    """Collapses rich or structured tool responses into a flat string payload.

    Extracts textual values from tool response lists, blocks, or dictionary mappings.

    Args:
        content: The raw response data returned by the tool call.

    Returns:
        A consolidated text representation of the response content.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                parts.append(block.get("text", str(block)))
            else:
                parts.append(str(block))
        return "\n".join(parts)
    return str(content) if content is not None else ""


async def execute(
    session: Any,
    tool_call: ToolCall,
) -> tuple[str, str | None]:
    """Executes a tool call via the active MCP session and processes its output.

    Applies safety guards to block attempts to pass raw artifact handles (e.g., 'art:NNNN')
    directly into file path or URL parameters. Large results exceeding 4 KB are
    persisted into the ArtifactStore, with a preview and artifact ID returned instead of
    the full payload.

    Args:
        session: The active MCP ClientSession object used to call the tool.
        tool_call: The structured ToolCall containing the tool name and arguments.

    Returns:
        A tuple of (result_text, artifact_id), where:
            - result_text: The tool outcome text or artifact preview message.
            - artifact_id: The stored artifact's ID if the output was large, otherwise None.
    """
    # Guard: block art: handles passed as path or url
    for key in ("path", "url"):
        val = tool_call.arguments.get(key, "")
        if isinstance(val, str) and val.startswith("art:"):
            return (
                f"Error: artifact handle '{val}' is not a file path or URL. "
                "Retrieve its contents first via get_artifact or use the attached bytes.",
                None,
            )

    result = await session.call_tool(tool_call.name, tool_call.arguments)
    text = _collapse_content(getattr(result, "content", result))

    if len(text.encode()) > _SIZE_LIMIT:
        content_type = "text/markdown" if tool_call.name == "fetch_url" else "text/plain"
        art_id = _store.put(
            text.encode(),
            content_type=content_type,
            source=tool_call.name,
            descriptor=f"{tool_call.name} result",
        )
        preview = text[:200]
        return f"[artifact {art_id}, {len(text.encode())} bytes] preview: {preview}", art_id

    return text, None
