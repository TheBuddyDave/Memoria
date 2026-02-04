"""
PostgreSQL Schema for Workflow Runtime State (MVP)
==================================================

Schema for managing application state.
See README.md in this directory for detailed usage scenarios and descriptions.

Tables:
-------
1. workflows        - Conversation-level metadata. One workflow = one conversation.
2. workflow_runs    - Execution state for a single user message (handles clarification pauses).
3. conversation_turns - Unit of interaction: User Input + Memories + AI Response (one complete interaction).
4. workflow_events  - Streaming events for WebSocket (auto-pruned and temporary).

Key Design Decisions:
---------------------
- WorkflowRun tracks the "in-process" state; ConversationTurn is only written when a full interaction is COMPLETED.
- JSONB fields store structured data that will be serialized to strings for LLM prompts.
- Clarification flow is handled via WorkflowRun.status = waiting_for_input + state checkpoint.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.mutable import MutableDict, MutableList
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


def utcnow() -> datetime:
    """Naive UTC timestamps for simplicity."""
    return datetime.now(timezone.utc)


# =============================================================================
# ENUMS
# =============================================================================


class WorkflowStatus(enum.Enum):
    """Status of the overall conversation/workflow."""

    active = "active"  # Conversation is ongoing
    archived = "archived"  # Conversation is closed/archived
    error = "error"  # Conversation encountered unrecoverable error


class RunStatus(enum.Enum):
    """
    Status of a single user message's processing lifecycle.

    State transitions:
      running -> waiting_for_input (if clarification needed)
      waiting_for_input -> running (when clarification received)
      running -> completed (normal finish, memories sent)
      running/waiting_for_input -> failed (error occurred)
      running/waiting_for_input -> cancelled (user cancelled)
    """

    running = "running"  # Currently executing workflow
    waiting_for_input = "waiting_for_input"  # Paused, waiting for clarification answer
    completed = "completed"  # Successfully finished, ConversationTurn written
    failed = "failed"  # Error during execution
    cancelled = "cancelled"  # User/system cancelled


# =============================================================================
# MODELS
# =============================================================================


class Workflow(Base):
    """
    Represents a single conversation thread.

    One workflow = one conversation with potentially many user messages (turns).
    The workflow persists across multiple turns and stores conversation-level context.

    Lifecycle:
    - Created when first message arrives with no workflow_id
    - Lives until archived or error state
    - Can have many WorkflowRuns (one per user message)
    - Can have many ConversationTurns (one per completed interaction)
    """

    __tablename__ = "workflows"

    # Primary identifier - returned to client, used for all subsequent requests
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    status: Mapped[WorkflowStatus] = mapped_column(
        Enum(WorkflowStatus, name="workflow_status", create_constraint=True),
        default=WorkflowStatus.active,
        nullable=False,
    )

    # Context Management - Rolling summary to prevent context bloat in long conversations
    # Updated periodically when conversation_turns grows too large
    summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Rolling conversation summary to prevent context bloat",
    )

    # Client preferences for this conversation (e.g., verbosity, domains)
    preferences: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(JSONB), default=dict, nullable=False
    )

    # Pointer to the most recent run - helps quickly determine if workflow is mid-execution
    # Used to detect: is this a new turn vs continuing a paused clarification?
    current_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflow_runs.id", use_alter=True),
        nullable=True,
    )

    # Error details if status = error
    error: Mapped[dict | None] = mapped_column(
        MutableDict.as_mutable(JSONB), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow, nullable=False
    )

    # Relationships
    runs: Mapped[list["WorkflowRun"]] = relationship(
        back_populates="workflow", # syncs both sides of the relationship without needing manual refresh.
        cascade="all, delete-orphan",  # when a workflow is deleted, delete its children runs
        passive_deletes=True,  # avoids loading children to memory to delete them, instead relies on DB cascade
        foreign_keys="WorkflowRun.workflow_id",
    )
    turns: Mapped[list["ConversationTurn"]] = relationship(
        back_populates="workflow", cascade="all, delete-orphan", passive_deletes=True
    )
    events: Mapped[list["WorkflowEvent"]] = relationship(
        back_populates="workflow", cascade="all, delete-orphan", passive_deletes=True
    )

    __table_args__ = (
        Index("ix_workflows_status", "status"),
        Index("ix_workflows_updated_at", "updated_at"),
    )


class WorkflowRun(Base):
    """
    Tracks the execution lifecycle of a SINGLE user message.

    This is the "in-flight" record that exists while we're processing a user message.
    It handles the state machine for clarification flow:
      - running: actively processing
      - waiting_for_input: paused for clarification (question stored in `state`)
      - completed: done, ConversationTurn has been written

    Key distinction from ConversationTurn:
    - WorkflowRun exists DURING processing (mutable, tracks progress)
    - ConversationTurn exists AFTER completion (immutable history record)

    The `message_id` is generated upfront and will become the ConversationTurn.message_id
    when the turn completes. This allows the client to track a message across the full lifecycle.
    """

    __tablename__ = "workflow_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
    )

    # message_id is assigned at run creation and becomes ConversationTurn.message_id on completion
    # This provides continuity for the client to track a message through its lifecycle
    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), unique=True, default=uuid.uuid4, nullable=False
    )

    status: Mapped[RunStatus] = mapped_column(
        Enum(RunStatus, name="run_status", create_constraint=True),
        default=RunStatus.running,
        nullable=False,
    )

    # The original user input that started this run
    user_input: Mapped[str] = mapped_column(Text, nullable=False)

    # Whether the subquery generator should ask clarifying questions
    ask_clarifications: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )

    # Runtime checkpoint state - stores data needed to resume after clarification
    # When status=waiting_for_input, this contains:
    #   {"pending_question": "What time period?", "clarifications_so_far": [...]}
    # Also stores intermediate results: subqueries, reasoningbank_hits, etc.
    state: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(JSONB),
        default=dict,
        nullable=False,
        comment="Checkpoint: pending_question, clarifications, intermediate results",
    )

    # Final output (memories) when run completes - also written to ConversationTurn
    final_output: Mapped[dict | None] = mapped_column(
        MutableDict.as_mutable(JSONB), nullable=True
    )

    # Error details if status = failed
    error: Mapped[dict | None] = mapped_column(
        MutableDict.as_mutable(JSONB), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow, nullable=False
    )

    # Relationships
    workflow: Mapped[Workflow] = relationship(
        back_populates="runs", foreign_keys=[workflow_id]
    )
    turn: Mapped["ConversationTurn"] = relationship(back_populates="run", uselist=False)
    events: Mapped[list["WorkflowEvent"]] = relationship(back_populates="run")

    __table_args__ = (
        Index("ix_workflow_runs_workflow_created", "workflow_id", "created_at"),
        Index("ix_workflow_runs_status", "workflow_id", "status"),
    )


class ConversationTurn(Base):
    """
    The permanent, immutable record of a COMPLETED interaction.

    This is the "source of truth" for conversation history used to build LLM prompts.
    One row = one complete interaction cycle:
      1. User Input (the original human message)
      2. Clarifications (if any Q&A happened)
      3. Retrieved Memories (what we sent to the AI agent)
      4. AI Response (what the AI agent replied to the human)

    IMPORTANT: This row is only created when:
      - WorkflowRun.status transitions to 'completed'
      - The /ai-answer endpoint has been called (AI response received)

    Until both conditions are met, data lives in WorkflowRun.state.

    Why separate from WorkflowRun?
    - WorkflowRun is mutable during execution
    - ConversationTurn is the clean, finalized record for prompt construction
    - Separating them makes history queries simpler and safer
    """

    __tablename__ = "conversation_turns"

    # Primary key - same as WorkflowRun.message_id for continuity
    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
    )

    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflow_runs.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    # =========================================================================
    # COMPONENT 1: User Input
    # =========================================================================
    user_input: Mapped[str] = mapped_column(
        Text, nullable=False, comment="The original user query that started this turn"
    )

    # =========================================================================
    # COMPONENT 2: Clarification History (Human-in-the-loop)
    # =========================================================================
    # List of {"question": str, "answer": str} for each clarification round
    # Example: [{"question": "Which region?", "answer": "Southeast"}]
    clarification_history: Mapped[list[dict] | None] = mapped_column(
        MutableList.as_mutable(JSONB),
        nullable=True,
        comment="List of {question, answer} clarification exchanges",
    )

    # =========================================================================
    # COMPONENT 3: System/Memory Output (what we sent to AI agent)
    # =========================================================================
    # Subqueries generated by SubqueryGenerator
    subqueries: Mapped[list | None] = mapped_column(
        MutableList.as_mutable(JSONB),
        nullable=True,
        comment="Decomposed subqueries from user input",
    )

    # Hits from ReasoningBank (run in parallel with subquery generation)
    reasoningbank_hits: Mapped[list[dict] | None] = mapped_column(
        MutableList.as_mutable(JSONB),
        nullable=True,
        comment="Reasoning patterns retrieved from vector DB",
    )

    # Final retrieved memories sent to the AI agent
    retrieved_memories: Mapped[list[dict] | None] = mapped_column(
        MutableList.as_mutable(JSONB),
        nullable=True,
        comment="Memory objects sent to AI agent (the main output)",
    )

    # =========================================================================
    # COMPONENT 4: AI Agent Response (received via /ai-answer endpoint)
    # =========================================================================
    ai_answer: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Final response the AI agent gave to the human user",
    )

    ai_reasoning: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="AI reasoning tokens/trace for debugging"
    )

    ai_tool_calls: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="History of AI tool calls/actions"
    )

    # =========================================================================
    # Metadata
    # =========================================================================
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow, nullable=False
    )

    # Relationships
    workflow: Mapped[Workflow] = relationship(back_populates="turns")
    run: Mapped[WorkflowRun] = relationship(back_populates="turn")

    __table_args__ = (
        # Index for fetching recent turns in a conversation (for prompt building)
        Index("ix_conversation_turns_workflow_created", "workflow_id", "created_at"),
    )


class WorkflowEvent(Base):
    """
    Ephemeral, append-only event stream for WebSocket clients.

    PURPOSE: Real-time streaming of workflow progress to clients.
    NOT FOR: Permanent history storage (use ConversationTurn for that).

    Design Principles:
    - SIMPLE: Just workflow_id, JSON payload, timestamp, and optional error flag
    - EPHEMERAL: Safe to delete after 24h or when run completes
    - CURSOR-BASED: Clients poll with (workflow_id, id > last_seen_id)

    Event payload format (flexible JSON):
    {
        "type": "progress" | "status" | "memories" | "error" | "complete",
        "message": "Human readable status...",
        "data": { ... optional structured data ... }
    }

    The 'is_final' flag marks the completion event - clients waiting for
    just the final answer can query: WHERE is_final = true
    """

    __tablename__ = "workflow_events"

    # Auto-incrementing ID serves as cursor for streaming
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Optional: link to specific run (useful for debugging, not required)
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflow_runs.id", ondelete="CASCADE"),
        nullable=True,
    )

    # The actual event content - simple JSON blob
    # Format: {"type": "...", "message": "...", "data": {...}}
    payload: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(JSONB),
        default=dict,
        nullable=False,
        comment="Event JSON: {type, message, data}",
    )

    # Marks the final event (contains memories) - allows O(1) lookup for final answer
    is_final: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="True for the completion event containing final memories",
    )

    # Quick error flag for filtering
    is_error: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="True if this event represents an error",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, nullable=False
    )

    # Relationships
    workflow: Mapped[Workflow] = relationship(back_populates="events")
    run: Mapped[WorkflowRun] = relationship(back_populates="events")

    __table_args__ = (
        # Primary cursor index: fetch events after cursor for a workflow
        Index("ix_workflow_events_cursor", "workflow_id", "id"),
        # Fast lookup for final answer only (no streaming)
        Index(
            "ix_workflow_events_final",
            "workflow_id",
            "is_final",
            postgresql_where="is_final = true",
        ),
    )
