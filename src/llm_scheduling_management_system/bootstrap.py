from pathlib import Path

from llm_scheduling_management_system.db import Base, engine, init_db
from llm_scheduling_management_system.logging import logger
from llm_scheduling_management_system.settings import settings


def reset_local_database() -> None:
    database_path = settings.database_path
    if database_path is None:
        raise RuntimeError("reset_local_database only supports sqlite file databases")

    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    if database_path.exists():
        database_path.unlink()
    init_db()
    logger.info("Reset local sqlite database at {}", database_path)


def ensure_local_database() -> Path | None:
    init_db()
    logger.info("Ensured local database exists")
    return settings.database_path
