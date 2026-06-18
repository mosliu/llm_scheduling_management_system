from sqlalchemy import select
from sqlalchemy.dialects import mysql
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateTable

from llm_scheduling_management_system.db import normalize_database_url
from llm_scheduling_management_system.domain.models import DocumentRecord, LLMInvocation, StepRun
from llm_scheduling_management_system.repositories.task_repository import TaskRepository
from llm_scheduling_management_system.schemas.tasks import CreateTaskRequest
from llm_scheduling_management_system.services.task_service import TaskService


def test_mysql_url_is_normalized_to_utf8mb4() -> None:
    normalized = normalize_database_url("mysql+pymysql://user:pass@127.0.0.1:3306/app?charset=utf8")

    url = make_url(normalized)

    assert url.query["charset"] == "utf8mb4"


def test_mysql_text_columns_compile_as_utf8mb4_longtext() -> None:
    document_ddl = str(CreateTable(DocumentRecord.__table__).compile(dialect=mysql.dialect()))
    llm_ddl = str(CreateTable(LLMInvocation.__table__).compile(dialect=mysql.dialect()))

    assert "content_text LONGTEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL" in document_ddl
    assert "CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci" in document_ddl
    assert "prompt_text LONGTEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL" in llm_ddl
    assert "response_text LONGTEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL" in llm_ddl


def test_repository_persists_long_unicode_document_content(session: Session) -> None:
    service = TaskService(session)
    task = service.create_task(
        CreateTaskRequest(
            template_id="event_summary_v1",
            input={"topic": "unicode document persistence"},
            options={},
        )
    )
    step = session.scalar(
        select(StepRun).where(
            StepRun.task_run_id == task.id,
            StepRun.node_key == "fetch_documents",
        )
    )
    assert step is not None

    content_text = ("济南法院参考性案例 住院记录 \U00100170\n" * 6000).strip()
    repository = TaskRepository(session)
    repository.advance_step(
        task=task,
        step=step,
        artifact_type="retrieval.fetched_documents",
        artifact_level="derived",
        schema_name="fetched_documents_bundle",
        schema_version="v1",
        content_json={
            "documents": [
                {
                    "provider": "exa_contents",
                    "url": "https://example.com/case.pdf",
                    "canonical_url": "https://example.com/case.pdf",
                    "title": "济南法院参考性案例",
                    "author": "研究室",
                    "language": "zh",
                    "source_domain": "example.com",
                    "source_type": "news",
                    "region_hint": "cn",
                    "publisher_type": "court",
                    "published_at_utc": None,
                    "content_text": content_text,
                    "metadata": {"source_url": "https://example.com/case.pdf"},
                }
            ]
        },
        content_text=content_text,
    )

    document = session.scalar(
        select(DocumentRecord).where(
            DocumentRecord.task_run_id == task.id,
            DocumentRecord.step_run_id == step.id,
        )
    )

    assert document is not None
    assert document.content_text == content_text
    assert document.title == "济南法院参考性案例"
