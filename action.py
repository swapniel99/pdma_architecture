from __future__ import annotations
from typing import Any

from artifacts import ArtifactStore
from schemas import ToolCall

_store = ArtifactStore()
_SIZE_LIMIT = 4096


def _collapse_content(content: Any) -> str:
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
        art_id = _store.put(
            text.encode(),
            content_type="text/plain",
            source=tool_call.name,
            descriptor=f"{tool_call.name} result",
        )
        preview = text[:200]
        return f"[artifact {art_id}, {len(text.encode())} bytes] preview: {preview}", art_id

    return text, None
