from __future__ import annotations
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from client import LLM
from schemas import MemoryItem, MemoryClassification, ToolCall

_MEMORY_PATH = Path("state/memory.json")
_STOPWORDS = {
    "a","an","the","is","in","on","at","to","for","of","and","or","it",
    "i","my","me","you","your","he","she","we","they","was","are","be",
    "this","that","with","from","by","as","up","do","if","so","but","not",
    "have","had","has","will","would","can","could","what","when","where",
    "who","how","about","into","than","then","also","just","some","more",
}

_llm = LLM()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _keywords_from_text(text: str) -> list[str]:
    words = text.lower().split()
    seen = set()
    out = []
    for w in words:
        clean = "".join(c for c in w if c.isalnum())
        if clean and clean not in _STOPWORDS and clean not in seen:
            seen.add(clean)
            out.append(clean)
    return out[:20]


def _overlap_score(kw_set: set[str], query_kws: set[str]) -> int:
    return len(kw_set & query_kws)


class Memory:
    def __init__(self, path: Path = _MEMORY_PATH):
        self._path = path
        self._items: list[MemoryItem] = []
        self._load()

    def _load(self):
        if self._path.exists():
            raw = json.loads(self._path.read_text())
            self._items = [MemoryItem(**item) for item in raw]

    def _save(self):
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
            item_kws = set(item.keywords)
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
        schema = MemoryClassification.model_json_schema()
        resp = _llm.chat(
            prompt=f"Find memory items most relevant to: {query}",
            auto_route="memory",
            max_tokens=512,
        )
        # fallback: keyword search
        return self.read(query, [], kinds=kinds, top_k=top_k)

    def remember(
        self,
        raw_text: str,
        source: str,
        run_id: str,
        goal_id: str | None = None,
    ) -> MemoryItem:
        schema = MemoryClassification.model_json_schema()
        resp = _llm.chat(
            prompt=raw_text,
            system="Classify this text into a memory item. Respond with valid JSON matching the schema.",
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
        kws = _keywords_from_text(tool_call.name)
        for v in tool_call.arguments.values():
            kws += _keywords_from_text(str(v))
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
