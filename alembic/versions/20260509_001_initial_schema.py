"""initial schema

Revision ID: 20260509_001
Revises: None
Create Date: 2026-05-09 12:40:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260509_001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "workflow_templates" not in existing_tables:
        op.create_table(
        "workflow_templates",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("latest_version", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )

    if "task_runs" not in existing_tables:
        op.create_table(
        "task_runs",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("template_id", sa.String(length=64), sa.ForeignKey("workflow_templates.id"), nullable=False),
        sa.Column("template_version", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("input_payload", sa.JSON(), nullable=False),
        sa.Column("options_payload", sa.JSON(), nullable=False),
        sa.Column("progress_percent", sa.Float(), nullable=False),
        sa.Column("current_step_run_id", sa.String(length=64), nullable=True),
        sa.Column("idempotency_key", sa.String(length=255), nullable=True),
        sa.Column("forked_from_task_run_id", sa.String(length=64), nullable=True),
        sa.Column("resume_from_checkpoint_id", sa.String(length=64), nullable=True),
        sa.Column("resume_from_artifact_id", sa.String(length=64), nullable=True),
        sa.Column("planned_step_count", sa.Integer(), nullable=False),
        sa.Column("completed_step_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        )

    if "step_runs" not in existing_tables:
        op.create_table(
        "step_runs",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("task_run_id", sa.String(length=64), sa.ForeignKey("task_runs.id"), nullable=False),
        sa.Column("node_key", sa.String(length=128), nullable=False),
        sa.Column("node_type", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("attempt_no", sa.Integer(), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("input_artifact_refs", sa.JSON(), nullable=False),
        sa.Column("input_snapshot", sa.JSON(), nullable=False),
        sa.Column("output_summary", sa.JSON(), nullable=False),
        sa.Column("cache_key", sa.String(length=255), nullable=True),
        sa.Column("cache_hit", sa.Boolean(), nullable=False),
        sa.Column("provider_snapshot", sa.JSON(), nullable=False),
        sa.Column("profile_snapshot", sa.JSON(), nullable=False),
        sa.Column("progress_percent", sa.Float(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )

    if "artifacts" not in existing_tables:
        op.create_table(
        "artifacts",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("task_run_id", sa.String(length=64), sa.ForeignKey("task_runs.id"), nullable=False),
        sa.Column("step_run_id", sa.String(length=64), sa.ForeignKey("step_runs.id"), nullable=True),
        sa.Column("artifact_type", sa.String(length=128), nullable=False),
        sa.Column("artifact_level", sa.String(length=32), nullable=False),
        sa.Column("schema_name", sa.String(length=128), nullable=False),
        sa.Column("schema_version", sa.String(length=32), nullable=False),
        sa.Column("content_json", sa.JSON(), nullable=False),
        sa.Column("content_text", sa.Text(), nullable=True),
        sa.Column("blob_uri", sa.String(length=1024), nullable=True),
        sa.Column("content_hash", sa.String(length=128), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("reusable_flag", sa.Boolean(), nullable=False),
        sa.Column("ttl_expire_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )

    if "artifact_lineage" not in existing_tables:
        op.create_table(
        "artifact_lineage",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("from_artifact_id", sa.String(length=64), sa.ForeignKey("artifacts.id"), nullable=False),
        sa.Column("to_artifact_id", sa.String(length=64), sa.ForeignKey("artifacts.id"), nullable=False),
        sa.Column("relation_type", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )

    if "checkpoints" not in existing_tables:
        op.create_table(
        "checkpoints",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("task_run_id", sa.String(length=64), sa.ForeignKey("task_runs.id"), nullable=False),
        sa.Column("step_run_id", sa.String(length=64), sa.ForeignKey("step_runs.id"), nullable=True),
        sa.Column("node_key", sa.String(length=128), nullable=False),
        sa.Column("checkpoint_type", sa.String(length=64), nullable=False),
        sa.Column("state_ref", sa.JSON(), nullable=False),
        sa.Column("artifact_refs", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        )

    if "search_invocations" not in existing_tables:
        op.create_table(
        "search_invocations",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("task_run_id", sa.String(length=64), sa.ForeignKey("task_runs.id"), nullable=False),
        sa.Column("step_run_id", sa.String(length=64), sa.ForeignKey("step_runs.id"), nullable=False),
        sa.Column("provider_name", sa.String(length=128), nullable=False),
        sa.Column("provider_vendor", sa.String(length=64), nullable=False),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("result_count", sa.Integer(), nullable=False),
        sa.Column("request_metadata", sa.JSON(), nullable=False),
        sa.Column("response_metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )

    if "fetch_invocations" not in existing_tables:
        op.create_table(
        "fetch_invocations",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("task_run_id", sa.String(length=64), sa.ForeignKey("task_runs.id"), nullable=False),
        sa.Column("step_run_id", sa.String(length=64), sa.ForeignKey("step_runs.id"), nullable=False),
        sa.Column("provider_name", sa.String(length=128), nullable=False),
        sa.Column("provider_vendor", sa.String(length=64), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("request_metadata", sa.JSON(), nullable=False),
        sa.Column("response_metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )

    if "llm_invocations" not in existing_tables:
        op.create_table(
        "llm_invocations",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("task_run_id", sa.String(length=64), sa.ForeignKey("task_runs.id"), nullable=False),
        sa.Column("step_run_id", sa.String(length=64), sa.ForeignKey("step_runs.id"), nullable=False),
        sa.Column("provider_name", sa.String(length=128), nullable=False),
        sa.Column("provider_type", sa.String(length=64), nullable=False),
        sa.Column("profile_name", sa.String(length=128), nullable=False),
        sa.Column("model_name", sa.String(length=128), nullable=False),
        sa.Column("prompt_text", sa.Text(), nullable=False),
        sa.Column("response_text", sa.Text(), nullable=False),
        sa.Column("request_metadata", sa.JSON(), nullable=False),
        sa.Column("response_metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )

    if "task_events" not in existing_tables:
        op.create_table(
        "task_events",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("task_run_id", sa.String(length=64), sa.ForeignKey("task_runs.id"), nullable=False),
        sa.Column("step_run_id", sa.String(length=64), sa.ForeignKey("step_runs.id"), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )

    if "search_hits" not in existing_tables:
        op.create_table(
        "search_hits",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("task_run_id", sa.String(length=64), sa.ForeignKey("task_runs.id"), nullable=False),
        sa.Column("step_run_id", sa.String(length=64), sa.ForeignKey("step_runs.id"), nullable=False),
        sa.Column("provider_name", sa.String(length=128), nullable=False),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("source_domain", sa.String(length=255), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("region_hint", sa.String(length=64), nullable=True),
        sa.Column("publisher_type", sa.String(length=64), nullable=True),
        sa.Column("snippet", sa.Text(), nullable=True),
        sa.Column("published_at_utc", sa.String(length=64), nullable=True),
        sa.Column("extra_metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )

    if "documents" not in existing_tables:
        op.create_table(
        "documents",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("task_run_id", sa.String(length=64), sa.ForeignKey("task_runs.id"), nullable=False),
        sa.Column("step_run_id", sa.String(length=64), sa.ForeignKey("step_runs.id"), nullable=False),
        sa.Column("provider_name", sa.String(length=128), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("canonical_url", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("author", sa.Text(), nullable=True),
        sa.Column("language", sa.String(length=64), nullable=True),
        sa.Column("source_domain", sa.String(length=255), nullable=True),
        sa.Column("source_type", sa.String(length=64), nullable=True),
        sa.Column("region_hint", sa.String(length=64), nullable=True),
        sa.Column("publisher_type", sa.String(length=64), nullable=True),
        sa.Column("published_at_utc", sa.String(length=64), nullable=True),
        sa.Column("content_text", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=128), nullable=True),
        sa.Column("extra_metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = set(inspector.get_table_names())

    for table_name in [
        "search_hits",
        "documents",
        "task_events",
        "fetch_invocations",
        "llm_invocations",
        "search_invocations",
        "checkpoints",
        "artifact_lineage",
        "artifacts",
        "step_runs",
        "task_runs",
        "workflow_templates",
    ]:
        if table_name in existing_tables:
            op.drop_table(table_name)
