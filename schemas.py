from __future__ import annotations
from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, model_validator, field_validator
import uuid


# ── Internal models ──────────────────────────────────────────────────────────

class MemoryItem(BaseModel):
    id: str
    kind: Literal["fact", "preference", "tool_outcome", "scratchpad"]
    keywords: list[str]
    descriptor: str
    value: str
    artifact_id: str | None = None
    source: str
    run_id: str
    goal_id: str | None = None
    confidence: float = 1.0
    created_at: datetime


class Artifact(BaseModel):
    id: str
    content_type: str
    size_bytes: int
    source: str
    descriptor: str


class Goal(BaseModel):
    id: str
    text: str
    done: bool = False
    attach_artifact_id: str | None = None


class Observation(BaseModel):
    goals: list[Goal] = []

    @property
    def all_done(self) -> bool:
        return bool(self.goals) and all(g.done for g in self.goals)

    def next_unfinished(self) -> Goal | None:
        for g in self.goals:
            if not g.done:
                return g
        return None


class ToolCall(BaseModel):
    name: str
    arguments: dict[str, Any] = {}


class DecisionOutput(BaseModel):
    answer: str | None = None
    tool_call: ToolCall | None = None

    @model_validator(mode="after")
    def exactly_one(self) -> "DecisionOutput":
        if (self.answer is None) == (self.tool_call is None):
            raise ValueError("exactly one of answer/tool_call must be set")
        return self

    @property
    def is_answer(self) -> bool:
        return self.answer is not None


# ── Wire models (LLM response_format) ────────────────────────────────────────

class PerceivedGoal(BaseModel):
    text: str
    done: bool = False
    artifact_index: int | None = None


class PerceptionResponse(BaseModel):
    goals: list[PerceivedGoal]


class MemoryClassification(BaseModel):
    kind: Literal["fact", "preference", "tool_outcome", "scratchpad"]
    keywords: list[str]
    descriptor: str
    value: str
    confidence: float = 1.0
