"""runtime schema sync

Revision ID: 20260509_002
Revises: 20260509_001
Create Date: 2026-05-09 16:55:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260509_002"
down_revision = "20260509_001"
branch_labels = None
depends_on = None


def _column_names(inspector, table_name: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "search_hits" in existing_tables:
        columns = _column_names(inspector, "search_hits")
        with op.batch_alter_table("search_hits") as batch_op:
            if "region_hint" not in columns:
                batch_op.add_column(sa.Column("region_hint", sa.String(length=64), nullable=True))
            if "publisher_type" not in columns:
                batch_op.add_column(sa.Column("publisher_type", sa.String(length=64), nullable=True))

    if "documents" in existing_tables:
        columns = _column_names(inspector, "documents")
        with op.batch_alter_table("documents") as batch_op:
            if "canonical_url" not in columns:
                batch_op.add_column(sa.Column("canonical_url", sa.Text(), nullable=True))
            if "author" not in columns:
                batch_op.add_column(sa.Column("author", sa.Text(), nullable=True))
            if "language" not in columns:
                batch_op.add_column(sa.Column("language", sa.String(length=64), nullable=True))
            if "region_hint" not in columns:
                batch_op.add_column(sa.Column("region_hint", sa.String(length=64), nullable=True))
            if "publisher_type" not in columns:
                batch_op.add_column(sa.Column("publisher_type", sa.String(length=64), nullable=True))

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
    # Downgrade is intentionally conservative for local MVP evolution.
    pass
