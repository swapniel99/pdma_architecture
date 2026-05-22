"""Module defining the Pydantic schemas and core data models for the MPDA system.

This module houses both internal models used for communication between the core
agent modules (Memory, Perception, Decision, and Action) and wire models used
for structured LLM response format validation.
"""

from __future__ import annotations
from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, model_validator


# ── Internal models ──────────────────────────────────────────────────────────

class MemoryItem(BaseModel):
    """Represents a single persistent entry in the agent's long-term memory.

    Memory items are classified and scored for retrieval based on keywords
    and semantic descriptors.

    Attributes:
        id: Unique identifier for the memory item (usually a UUID).
        kind: The type of memory. One of:
            - "fact": Extracted user facts or system observations.
            - "preference": User-specified preferences or style guidelines.
            - "tool_outcome": Summarized result of executing a tool call.
            - "scratchpad": Temporary thoughts or chain-of-thought steps.
        keywords: List of search keywords extracted from the content for indexing.
        descriptor: A brief human-readable summary of what this memory is about.
        value: The raw memory payload containing structured data.
        artifact_id: Reference to an associated artifact ID in the ArtifactStore, if any.
        source: The originating entity of the memory (e.g., "user", "action", "perception").
        run_id: Identifier of the specific agent execution run where this was created.
        goal_id: Optional ID of the goal during which this memory was recorded.
        confidence: Confidence score of the memory extraction (0.0 to 1.0).
        created_at: Timestamp of when the memory item was recorded.
    """
    id: str
    kind: Literal["fact", "preference", "tool_outcome", "scratchpad"]
    keywords: list[str]
    descriptor: str
    value: dict[str, Any]
    artifact_id: str | None = None
    source: str
    run_id: str
    goal_id: str | None = None
    confidence: float = 1.0
    created_at: datetime


class Artifact(BaseModel):
    """Metadata representing a large data payload stored in the ArtifactStore.

    Used when tool outcomes or content are too large (e.g., >4 KB) to be stored
    directly in a MemoryItem value or passed directly in LLM prompts.

    Attributes:
        id: The sequential artifact handle/ID (e.g., 'art:0001').
        content_type: The MIME/content type of the artifact (e.g., 'text/html', 'application/json').
        size_bytes: The total size of the raw artifact data in bytes.
        source: The tool or process that generated this artifact (e.g., 'fetch_url').
        descriptor: A short description of the artifact content.
    """
    id: str
    content_type: str
    size_bytes: int
    source: str
    descriptor: str


class Goal(BaseModel):
    """Represents a specific objective or task in the agent's execution plan.

    Goals are structured tasks managed by the perception module and executed
    one-by-one by the decision and action modules.

    Attributes:
        id: Positional identifier of the goal (typically generated sequentially, e.g., 'goal_0').
        text: Description of the goal to be achieved.
        done: True if the perception module has determined this goal is completed.
        attach_artifact_id: Optional artifact ID to attach as context for decision making.
    """
    id: str
    text: str
    done: bool = False
    attach_artifact_id: str | None = None


class Observation(BaseModel):
    """Wraps the current set of goals perceived by the perception module.

    Acts as the main state container indicating what tasks are completed and
    what the agent should work on next.

    Attributes:
        goals: List of goals in their original sequential execution order.
    """
    goals: list[Goal] = []

    @property
    def all_done(self) -> bool:
        """Checks if all goals in the observation have been completed.

        Returns:
            True if there is at least one goal and all of them are marked done,
            otherwise False.
        """
        return bool(self.goals) and all(g.done for g in self.goals)

    def next_unfinished(self) -> Goal | None:
        """Finds the first unfinished goal in the sequential list.

        Returns:
            The first Goal that is not marked done, or None if all goals
            are completed or the list is empty.
        """
        for g in self.goals:
            if not g.done:
                return g
        return None


class ToolCall(BaseModel):
    """Represents a request to execute a specific tool via the MCP server.

    Attributes:
        name: The exact name of the tool to invoke (e.g., 'web_search').
        arguments: A dictionary of arguments to pass to the tool.
    """
    name: str
    arguments: dict[str, Any] = {}


class DecisionOutput(BaseModel):
    """The structured output of a single decision step.

    A decision step must produce exactly one of a final/partial answer or
    a tool call to execute.

    Attributes:
        answer: The final or partial answer string, if the goal is answered.
        tool_call: The tool call details, if further action is needed to progress.
    """
    answer: str | None = None
    tool_call: ToolCall | None = None

    @model_validator(mode="after")
    def exactly_one(self) -> "DecisionOutput":
        """Validates that exactly one of `answer` or `tool_call` is provided.

        Raises:
            ValueError: If both are None or both are set.
        """
        if (self.answer is None) == (self.tool_call is None):
            raise ValueError("exactly one of answer/tool_call must be set")
        return self

    @property
    def is_answer(self) -> bool:
        """Checks if this decision output is a final or partial answer.

        Returns:
            True if the answer field is populated, otherwise False.
        """
        return self.answer is not None


# ── Wire models (LLM response_format) ────────────────────────────────────────

class PerceivedGoal(BaseModel):
    """LLM wire format representation of a single goal.

    Used by the perception module to parse LLM structured outputs before
    resolving references (such as mapping artifact_index to artifact_id).

    Attributes:
        text: The description of the goal.
        done: True if the goal is perceived to be completed.
        artifact_index: Optional index pointing to an artifact in the history.
    """
    text: str
    done: bool = False
    artifact_index: int | None = None


class PerceptionResponse(BaseModel):
    """LLM wire format wrapping the list of perceived goals.

    Attributes:
        goals: List of perceived goals parsed from the perception LLM output.
    """
    goals: list[PerceivedGoal]


class MemoryClassification(BaseModel):
    """LLM wire format used for classifying new memory items.

    Enables structured LLM output validation when creating or classifying
    unstructured text into categorized memory entries.

    Attributes:
        kind: The categorized type of the memory item.
        keywords: Important search terms extracted from the memory text.
        descriptor: Brief summary descriptor of the classified memory.
        value: Structured dictionary representation of the memory content.
        confidence: Confidence score assigned to the classification (0.0 to 1.0).
    """
    kind: Literal["fact", "preference", "tool_outcome", "scratchpad"]
    keywords: list[str]
    descriptor: str
    value: dict[str, Any]
    confidence: float = 1.0
