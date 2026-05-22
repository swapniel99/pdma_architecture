"""Module for managing the agent's long-term memory store.

Memory entries consist of key-value attributes classified by their categories,
with support for rapid keyword overlap queries, structured filtering, and LLM-driven
relevance ranking for context window optimization.
"""

from __future__ import annotations
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from client import LLM
from schemas import MemoryItem, MemoryClassification, ToolCall

_MEMORY_PATH = Path("state/memory.json")
_CLASSIFY_PROMPT = (Path(__file__).parent / "prompts" / "memory_classify.txt").read_text()
_STOPWORDS = {
    "a","an","the","is","in","on","at","to","for","of","and","or","it",
    "i","my","me","you","your","he","she","we","they","was","are","be",
    "this","that","with","from","by","as","up","do","if","so","but","not",
    "have","had","has","will","would","can","could","what","when","where",
    "who","how","about","into","than","then","also","just","some","more",
}

_llm = LLM()


def _now() -> datetime:
    """Returns the current timezone-aware UTC datetime.

    Returns:
        The current datetime with timezone set to UTC.
    """
    return datetime.now(timezone.utc)


def _keywords_from_url(url: str) -> list[str]:
    import re
    parts = re.split(r'[/:._\-?&=]+', url)
    seen: set[str] = set()
    out: list[str] = []
    for w in parts:
        w = w.lower()
        if w and len(w) > 2 and w not in _STOPWORDS and w not in seen:
            seen.add(w)
            out.append(w)
    return out[:20]


def _keywords_from_text(text: str) -> list[str]:
    """Extracts unique, lowercased alphanumeric keywords from the given text.

    Filters out standard grammatical stopwords and limits the returned list
    to the top 20 keywords. URLs are split on path separators to yield
    meaningful tokens rather than one concatenated blob.

    Args:
        text: The source string to extract keywords from.

    Returns:
        A list of up to 20 unique keyword strings.
    """
    words = text.lower().split()
    seen: set[str] = set()
    out: list[str] = []
    for w in words:
        if w.startswith("http://") or w.startswith("https://"):
            for kw in _keywords_from_url(w):
                if kw not in seen:
                    seen.add(kw)
                    out.append(kw)
        else:
            clean = "".join(c for c in w if c.isalnum())
            if clean and clean not in _STOPWORDS and clean not in seen:
                seen.add(clean)
                out.append(clean)
    return out[:20]


def _overlap_score(kw_set: set[str], query_kws: set[str]) -> int:
    """Calculates the size of the intersection between two keyword sets.

    Args:
        kw_set: The keywords associated with a memory item.
        query_kws: The keywords extracted from the search query/context.

    Returns:
        The number of matching keywords common to both sets.
    """
    return len(kw_set & query_kws)


class Memory:
    """A typed key-value persistent memory store for the cognitive agent.

    Allows loading, saving, querying, and recording facts, preferences,
    tool execution outcomes, and scratchpad thoughts.
    """

    def __init__(self, path: Path = _MEMORY_PATH):
        """Initializes the memory store and loads existing entries from disk.

        Args:
            path: The filesystem path to the persistent JSON memory file.
        """
        self._path = path
        self._items: list[MemoryItem] = []
        self._load()

    def _load(self):
        """Loads and parses persisted memory items from the JSON file on disk.

        Instantiates stored dictionaries back into `MemoryItem` Pydantic models.
        """
        if self._path.exists():
            raw = json.loads(self._path.read_text())
            self._items = [MemoryItem(**item) for item in raw]

    def _save(self):
        """Serializes and writes all current memory items to the persistent JSON file.

        Creates parent directories automatically if they do not exist.
        """
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps([item.model_dump(mode="json") for item in self._items], indent=2)
        )

    def read(
        self,
        query: str,
        history: list[dict],
        kinds: list[str] | None = None,
        top_k: int = 8,
    ) -> list[MemoryItem]:
        """Performs a fast, non-LLM keyword-overlap search across memory candidates.

        Combines keywords from both the query and the last five history items to score
        matching candidates based on keyword overlap.

        Args:
            query: The current query/search string.
            history: The list of preceding execution step dictionaries.
            kinds: Optional list of memory kinds to restrict candidates to.
            top_k: The maximum number of high-scoring memory items to return.

        Returns:
            A list of up to `top_k` matching MemoryItem instances, sorted in descending
            order of overlap score.
        """
        query_kws = set(_keywords_from_text(query))
        history_text = " ".join(
            str(h.get("content") or h.get("text") or "") for h in history[-5:]
        )
        history_kws = set(_keywords_from_text(history_text))
        all_kws = query_kws | history_kws

        candidates = self._items
        if kinds:
            candidates = [i for i in candidates if i.kind in kinds]

        scored = []
        for item in candidates:
            item_kws = set(k.lower() for k in item.keywords) | set(_keywords_from_text(item.descriptor))
            score = _overlap_score(item_kws, all_kws)
            if score > 0:
                scored.append((score, item))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:top_k]]

    def filter(
        self,
        kinds: list[str] | None = None,
        goal_id: str | None = None,
        recent: int | None = None,
    ) -> list[MemoryItem]:
        """Performs structured filtering of memory items without keyword scoring.

        Args:
            kinds: Optional list of memory kinds to include (e.g., ['fact']).
            goal_id: Optional goal ID to filter by.
            recent: Optional integer to limit results to the most recent N items.

        Returns:
            A filtered list of MemoryItem instances matching the criteria.
        """
        result = self._items
        if kinds:
            result = [i for i in result if i.kind in kinds]
        if goal_id is not None:
            result = [i for i in result if i.goal_id == goal_id]
        if recent is not None:
            result = result[-recent:]
        return result

    def relevant(
        self,
        query: str,
        kinds: list[str] | None = None,
        top_k: int = 5,
    ) -> list[MemoryItem]:
        """Finds the most semantically relevant memories using LLM ranking.

        If the total memory pool is large (>20 entries), a keyword search pre-filter is
        applied first to protect the prompt context window. The LLM then ranks the
        remaining candidates. Falls back to keyword search on ranking failures.

        Args:
            query: The search query to assess relevance against.
            kinds: Optional list of memory kinds to restrict search.
            top_k: The maximum number of relevant memories to retrieve.

        Returns:
            A list of up to `top_k` ranked MemoryItem instances.
        """
        candidates = self._items
        if kinds:
            candidates = [i for i in candidates if i.kind in kinds]
        if not candidates:
            return []

        # Pre-filter large pools with keyword search to keep prompt small
        if len(candidates) > 20:
            candidates = self.read(query, [], kinds=kinds, top_k=20)

        lines = [f"[{i}] {c.descriptor}: {c.value}" for i, c in enumerate(candidates)]
        resp = _llm.chat(
            prompt=(
                f"Query: {query}\n\nCandidates:\n" + "\n".join(lines) +
                f"\n\nReturn a JSON array of the {top_k} most relevant indices (integers only). Example: [0,2]"
            ),
            auto_route="memory",
            max_tokens=64,
            temperature=0.1,
        )

        try:
            text = resp.get("text", "")
            start = text.find("[")
            end = text.rfind("]") + 1
            if start != -1 and end > start:
                indices = json.loads(text[start:end])
                result = [candidates[i] for i in indices if isinstance(i, int) and 0 <= i < len(candidates)]
                if result:
                    return result[:top_k]
        except Exception:
            pass

        return self.read(query, [], kinds=kinds, top_k=top_k)

    def remember(
        self,
        raw_text: str,
        source: str,
        run_id: str,
        goal_id: str | None = None,
    ) -> MemoryItem | None:
        """Classifies and adds a new piece of information to the memory store.

        Uses the LLM to classify unstructured text into a structured memory format,
        extracting keywords, kind, confidence, and a descriptor. Falls back to a
        scratchpad classification if LLM parsing fails.

        Args:
            raw_text: The raw text string to remember and classify.
            source: The originating source of the text (e.g., 'user', 'perception').
            run_id: The active agent execution run identifier.
            goal_id: Optional ID of the goal during which this memory was created.

        Returns:
            The newly created and persisted MemoryItem instance.
        """
        schema = MemoryClassification.model_json_schema()
        resp = _llm.chat(
            prompt=raw_text,
            system=_CLASSIFY_PROMPT,
            auto_route='memory',
            response_format={"type": "json_schema", "schema": schema},
            max_tokens=512,
            temperature=0.3,
        )

        parsed = resp.get("parsed")
        if parsed and isinstance(parsed, dict):
            mc = MemoryClassification(**parsed)
        else:
            text = resp.get("text", "")
            try:
                data = json.loads(text)
                mc = MemoryClassification(**data)
            except Exception:
                mc = MemoryClassification(
                    kind="scratchpad",
                    keywords=_keywords_from_text(raw_text),
                    descriptor=raw_text[:80],
                    value={"text": raw_text},
                    confidence=0.5,
                )

        if mc.kind == "none":
            return None

        item = MemoryItem(
            id=str(uuid.uuid4()),
            kind=mc.kind,
            keywords=mc.keywords,
            descriptor=mc.descriptor,
            value=mc.value,
            confidence=mc.confidence,
            source=source,
            run_id=run_id,
            goal_id=goal_id,
            created_at=_now(),
        )
        self._items.append(item)
        self._save()
        return item

    def record_outcome(
        self,
        tool_call: ToolCall,
        result_text: str,
        artifact_id: str | None,
        run_id: str,
        goal_id: str | None = None,
    ) -> MemoryItem:
        """Records the outcome of a tool execution as a typed memory item.

        Constructs a structured `tool_outcome` MemoryItem without calling the LLM,
        summarizing arguments, result snippets, and any associated artifact IDs.

        Args:
            tool_call: The ToolCall instance containing the tool name and arguments.
            result_text: The return value or outcome text from executing the tool.
            artifact_id: The ID of an out-of-band artifact if the result was large.
            run_id: The active agent execution run identifier.
            goal_id: Optional ID of the goal associated with this tool execution.

        Returns:
            The recorded and persisted `tool_outcome` MemoryItem.
        """
        kws = _keywords_from_text(tool_call.name)
        for v in tool_call.arguments.values():
            s = str(v)
            if s.startswith("http://") or s.startswith("https://"):
                kws += _keywords_from_url(s)
            else:
                kws += _keywords_from_text(s)
        kws = list(dict.fromkeys(kws))[:20]

        descriptor = f"{tool_call.name}({', '.join(f'{k}={v}' for k,v in list(tool_call.arguments.items())[:3])})"
        value = {"result": result_text[:500] if result_text else ""}

        item = MemoryItem(
            id=str(uuid.uuid4()),
            kind="tool_outcome",
            keywords=kws,
            descriptor=descriptor,
            value=value,
            artifact_id=artifact_id,
            source="action",
            run_id=run_id,
            goal_id=goal_id,
            created_at=_now(),
        )
        self._items.append(item)
        self._save()
        return item
