"""ensure mysql utf8mb4 long text storage

Revision ID: 20260618_003
Revises: 20260509_002
Create Date: 2026-06-18 15:45:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260618_003"
down_revision = "20260509_002"
branch_labels = None
depends_on = None

MYSQL_UTF8MB4_CHARSET = "utf8mb4"
MYSQL_UTF8MB4_COLLATION = "utf8mb4_unicode_ci"

TABLE_NAMES = [
    "workflow_templates",
    "task_runs",
    "step_runs",
    "artifacts",
    "artifact_lineage",
    "checkpoints",
    "search_invocations",
    "fetch_invocations",
    "llm_invocations",
    "task_events",
    "search_hits",
    "documents",
]

TEXT_COLUMNS_BY_TABLE = {
    "workflow_templates": [("description", True)],
    "step_runs": [("error_message", True)],
    "artifacts": [("content_text", True)],
    "search_invocations": [("query_text", False)],
    "fetch_invocations": [("url", False), ("title", True)],
    "llm_invocations": [("prompt_text", False), ("response_text", False)],
    "search_hits": [
        ("query_text", False),
        ("title", False),
        ("snippet", True),
    ],
    "documents": [
        ("url", False),
        ("canonical_url", True),
        ("title", True),
        ("author", True),
        ("content_text", False),
    ],
}


def _quote_mysql_identifier(identifier: str) -> str:
    return f"`{identifier.replace('`', '``')}`"


def _existing_tables(bind, schema_name: str) -> set[str]:
    return set(
        bind.execute(
            sa.text(
                """
                SELECT TABLE_NAME
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = :schema_name
                """
            ),
            {"schema_name": schema_name},
        ).scalars()
    )


def _column_info(bind, schema_name: str, table_name: str) -> dict[str, dict]:
    rows = bind.execute(
        sa.text(
            """
            SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_SET_NAME, COLLATION_NAME
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = :schema_name AND TABLE_NAME = :table_name
            """
        ),
        {"schema_name": schema_name, "table_name": table_name},
    ).mappings()
    return {row["COLUMN_NAME"]: dict(row) for row in rows}


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name not in {"mysql", "mariadb"}:
        return

    schema_name = bind.execute(sa.text("SELECT DATABASE()")).scalar_one_or_none()
    if not schema_name:
        return

    existing_tables = _existing_tables(bind, schema_name)

    for table_name in TABLE_NAMES:
        if table_name not in existing_tables:
            continue
        op.execute(
            sa.text(
                f"ALTER TABLE {_quote_mysql_identifier(table_name)} "
                f"DEFAULT CHARACTER SET {MYSQL_UTF8MB4_CHARSET} "
                f"COLLATE {MYSQL_UTF8MB4_COLLATION}"
            )
        )

    for table_name, text_columns in TEXT_COLUMNS_BY_TABLE.items():
        if table_name not in existing_tables:
            continue
        columns = _column_info(bind, schema_name, table_name)
        quoted_table = _quote_mysql_identifier(table_name)
        for column_name, nullable in text_columns:
            row = columns.get(column_name)
            if row is None:
                continue
            needs_longtext = str(row["DATA_TYPE"]).lower() != "longtext"
            needs_charset = row["CHARACTER_SET_NAME"] != MYSQL_UTF8MB4_CHARSET
            needs_collation = not str(row["COLLATION_NAME"] or "").startswith(MYSQL_UTF8MB4_CHARSET)
            if not (needs_longtext or needs_charset or needs_collation):
                continue
            null_sql = "NULL" if nullable else "NOT NULL"
            op.execute(
                sa.text(
                    f"ALTER TABLE {quoted_table} MODIFY {_quote_mysql_identifier(column_name)} "
                    f"LONGTEXT CHARACTER SET {MYSQL_UTF8MB4_CHARSET} "
                    f"COLLATE {MYSQL_UTF8MB4_COLLATION} {null_sql}"
                )
            )


def downgrade() -> None:
    # Do not shrink or re-encode text columns; that could truncate stored artifacts.
    pass
