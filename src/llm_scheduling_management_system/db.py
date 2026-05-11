from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from llm_scheduling_management_system.settings import settings


class Base(DeclarativeBase):
    pass


def _ensure_sqlite_parent_exists() -> None:
    database_path = settings.database_path
    if database_path is None:
        return

    parent = database_path.parent
    if parent != Path("."):
        parent.mkdir(parents=True, exist_ok=True)


_ensure_sqlite_parent_exists()

engine = create_engine(
    settings.database_url,
    future=True,
    echo=False,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)


def init_db() -> None:
    # Import models here so SQLAlchemy metadata is populated before create_all runs.
    from llm_scheduling_management_system.domain import models  # noqa: F401

    Base.metadata.create_all(bind=engine)


def get_db_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
