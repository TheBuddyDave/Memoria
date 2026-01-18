"""
Docstring for src.database.agent_state.models

This is where we define all the ORM models (tables) and their schema (columns, relationships, etc.) for the agent_state database.
If you want to change the database schema, make changes here and run create_tables.py to apply them.
"""
import uuid
from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.ext.mutable import MutableDict

from .base import Base


class Workflow(Base):
    __tablename__ = "workflows"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")

    # JSONB that we mutate in-place => MutableDict.as_mutable(JSONB)
    context: Mapped[dict] = mapped_column(MutableDict.as_mutable(JSONB), nullable=False, default=dict)
    preferences: Mapped[dict] = mapped_column(MutableDict.as_mutable(JSONB), nullable=False, default=dict)

    # Your tweak
    important_steps: Mapped[dict] = mapped_column(MutableDict.as_mutable(JSONB), nullable=False, default=dict)

    most_recent_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflow_runs.id", ondelete="SET NULL"),
        nullable=True,
    )

    error: Mapped[dict | None] = mapped_column(MutableDict.as_mutable(JSONB), nullable=True)

    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(String(32), nullable=False, default="running", index=True)

    user_input: Mapped[str] = mapped_column(Text, nullable=False)

    ask_clarifications: Mapped[bool] = mapped_column(nullable=False, default=True)

    state: Mapped[dict] = mapped_column(MutableDict.as_mutable(JSONB), nullable=False, default=dict)

    final_output: Mapped[dict | None] = mapped_column(MutableDict.as_mutable(JSONB), nullable=True)
    error: Mapped[dict | None] = mapped_column(MutableDict.as_mutable(JSONB), nullable=True)

    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    __table_args__ = (
        Index(
            "ix_workflow_runs_workflow_id_status",
            "workflow_id",
            "status",
        ),
    )


class WorkflowEvent(Base):
    __tablename__ = "workflow_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflow_runs.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    kind: Mapped[str] = mapped_column(String(32), nullable=False, default="progress")
    text: Mapped[str] = mapped_column(Text, nullable=False)

    payload: Mapped[dict] = mapped_column(MutableDict.as_mutable(JSONB), nullable=False, default=dict)

    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_workflow_events_workflow_id_id", "workflow_id", "id"),
    )
