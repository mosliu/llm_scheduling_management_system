from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from llm_scheduling_management_system.db import Base
from llm_scheduling_management_system.domain.enums import ArtifactLevel, StepStatus, TaskStatus


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def generate_prefixed_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:24]}"


class WorkflowTemplate(Base):
    __tablename__ = "workflow_templates"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(128), nullable=False, default="general")
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    latest_version: Mapped[str] = mapped_column(String(32), nullable=False, default="v1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    task_runs: Mapped[list[TaskRun]] = relationship(back_populates="template")


class TaskRun(Base):
    __tablename__ = "task_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: generate_prefixed_id("run"))
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, default="default")
    template_id: Mapped[str] = mapped_column(ForeignKey("workflow_templates.id"), nullable=False)
    template_version: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=TaskStatus.QUEUED.value)
    input_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    options_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    progress_percent: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    current_step_run_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    forked_from_task_run_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resume_from_checkpoint_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resume_from_artifact_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    planned_step_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_step_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    template: Mapped[WorkflowTemplate] = relationship(back_populates="task_runs")
    step_runs: Mapped[list[StepRun]] = relationship(back_populates="task_run", cascade="all, delete-orphan")
    artifacts: Mapped[list[Artifact]] = relationship(back_populates="task_run", cascade="all, delete-orphan")
    checkpoints: Mapped[list[Checkpoint]] = relationship(back_populates="task_run", cascade="all, delete-orphan")


class StepRun(Base):
    __tablename__ = "step_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: generate_prefixed_id("step"))
    task_run_id: Mapped[str] = mapped_column(ForeignKey("task_runs.id"), nullable=False)
    node_key: Mapped[str] = mapped_column(String(128), nullable=False)
    node_type: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=StepStatus.PENDING.value)
    attempt_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    input_artifact_refs: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    input_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    output_summary: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    cache_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cache_hit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    provider_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    profile_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    progress_percent: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    task_run: Mapped[TaskRun] = relationship(back_populates="step_runs")
    artifacts: Mapped[list[Artifact]] = relationship(back_populates="step_run", cascade="all, delete-orphan")
    checkpoints: Mapped[list[Checkpoint]] = relationship(back_populates="step_run", cascade="all, delete-orphan")


class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: generate_prefixed_id("art"))
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, default="default")
    task_run_id: Mapped[str] = mapped_column(ForeignKey("task_runs.id"), nullable=False)
    step_run_id: Mapped[str | None] = mapped_column(ForeignKey("step_runs.id"), nullable=True)
    artifact_type: Mapped[str] = mapped_column(String(128), nullable=False)
    artifact_level: Mapped[str] = mapped_column(String(32), nullable=False, default=ArtifactLevel.DERIVED.value)
    schema_name: Mapped[str] = mapped_column(String(128), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(32), nullable=False, default="v1")
    content_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    content_text: Mapped[str | None] = mapped_column(Text(), nullable=True)
    blob_uri: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reusable_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    ttl_expire_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    task_run: Mapped[TaskRun] = relationship(back_populates="artifacts")
    step_run: Mapped[StepRun | None] = relationship(back_populates="artifacts")


class ArtifactLineage(Base):
    __tablename__ = "artifact_lineage"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: generate_prefixed_id("lin"))
    from_artifact_id: Mapped[str] = mapped_column(ForeignKey("artifacts.id"), nullable=False)
    to_artifact_id: Mapped[str] = mapped_column(ForeignKey("artifacts.id"), nullable=False)
    relation_type: Mapped[str] = mapped_column(String(64), nullable=False, default="derived_from")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class SearchInvocation(Base):
    __tablename__ = "search_invocations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: generate_prefixed_id("sinv"))
    task_run_id: Mapped[str] = mapped_column(ForeignKey("task_runs.id"), nullable=False)
    step_run_id: Mapped[str] = mapped_column(ForeignKey("step_runs.id"), nullable=False)
    provider_name: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_vendor: Mapped[str] = mapped_column(String(64), nullable=False)
    query_text: Mapped[str] = mapped_column(Text(), nullable=False)
    result_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    request_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    response_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class FetchInvocation(Base):
    __tablename__ = "fetch_invocations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: generate_prefixed_id("finv"))
    task_run_id: Mapped[str] = mapped_column(ForeignKey("task_runs.id"), nullable=False)
    step_run_id: Mapped[str] = mapped_column(ForeignKey("step_runs.id"), nullable=False)
    provider_name: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_vendor: Mapped[str] = mapped_column(String(64), nullable=False)
    url: Mapped[str] = mapped_column(Text(), nullable=False)
    title: Mapped[str | None] = mapped_column(Text(), nullable=True)
    request_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    response_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class LLMInvocation(Base):
    __tablename__ = "llm_invocations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: generate_prefixed_id("linv"))
    task_run_id: Mapped[str] = mapped_column(ForeignKey("task_runs.id"), nullable=False)
    step_run_id: Mapped[str] = mapped_column(ForeignKey("step_runs.id"), nullable=False)
    provider_name: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_type: Mapped[str] = mapped_column(String(64), nullable=False)
    profile_name: Mapped[str] = mapped_column(String(128), nullable=False)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt_text: Mapped[str] = mapped_column(Text(), nullable=False)
    response_text: Mapped[str] = mapped_column(Text(), nullable=False)
    request_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    response_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class TaskEvent(Base):
    __tablename__ = "task_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: generate_prefixed_id("tev"))
    task_run_id: Mapped[str] = mapped_column(ForeignKey("task_runs.id"), nullable=False)
    step_run_id: Mapped[str | None] = mapped_column(ForeignKey("step_runs.id"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class ToolInvocation(Base):
    __tablename__ = "tool_invocations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: generate_prefixed_id("tinv"))
    task_run_id: Mapped[str] = mapped_column(ForeignKey("task_runs.id"), nullable=False)
    step_run_id: Mapped[str] = mapped_column(ForeignKey("step_runs.id"), nullable=False)
    server_name: Mapped[str] = mapped_column(String(128), nullable=False)
    tool_name: Mapped[str] = mapped_column(String(128), nullable=False)
    arguments_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    response_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="completed")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class SearchHitRecord(Base):
    __tablename__ = "search_hits"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: generate_prefixed_id("shit"))
    task_run_id: Mapped[str] = mapped_column(ForeignKey("task_runs.id"), nullable=False)
    step_run_id: Mapped[str] = mapped_column(ForeignKey("step_runs.id"), nullable=False)
    provider_name: Mapped[str] = mapped_column(String(128), nullable=False)
    query_text: Mapped[str] = mapped_column(Text(), nullable=False)
    title: Mapped[str] = mapped_column(Text(), nullable=False)
    source_domain: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    region_hint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    publisher_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    snippet: Mapped[str | None] = mapped_column(Text(), nullable=True)
    published_at_utc: Mapped[str | None] = mapped_column(String(64), nullable=True)
    extra_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class DocumentRecord(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: generate_prefixed_id("doc"))
    task_run_id: Mapped[str] = mapped_column(ForeignKey("task_runs.id"), nullable=False)
    step_run_id: Mapped[str] = mapped_column(ForeignKey("step_runs.id"), nullable=False)
    provider_name: Mapped[str] = mapped_column(String(128), nullable=False)
    url: Mapped[str] = mapped_column(Text(), nullable=False)
    canonical_url: Mapped[str | None] = mapped_column(Text(), nullable=True)
    title: Mapped[str | None] = mapped_column(Text(), nullable=True)
    author: Mapped[str | None] = mapped_column(Text(), nullable=True)
    language: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    region_hint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    publisher_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    published_at_utc: Mapped[str | None] = mapped_column(String(64), nullable=True)
    content_text: Mapped[str] = mapped_column(Text(), nullable=False)
    content_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    extra_metadata: Mapped[dict] = mapped_column(JSON(), nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class Checkpoint(Base):
    __tablename__ = "checkpoints"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: generate_prefixed_id("cp"))
    task_run_id: Mapped[str] = mapped_column(ForeignKey("task_runs.id"), nullable=False)
    step_run_id: Mapped[str | None] = mapped_column(ForeignKey("step_runs.id"), nullable=True)
    node_key: Mapped[str] = mapped_column(String(128), nullable=False)
    checkpoint_type: Mapped[str] = mapped_column(String(64), nullable=False, default="artifact_boundary")
    state_ref: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    artifact_refs: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    task_run: Mapped[TaskRun] = relationship(back_populates="checkpoints")
    step_run: Mapped[StepRun | None] = relationship(back_populates="checkpoints")
