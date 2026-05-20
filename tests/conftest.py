import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["LSMS_SEARCH_CONFIG_PATH"] = "config/search.example.toml"
os.environ["LSMS_LLM_CONFIG_PATH"] = "config/llm.example.toml"
os.environ["LSMS_SOURCE_REGISTRY_CONFIG_PATH"] = "config/source_registry.example.toml"
os.environ["LSMS_ACCESS_CONFIG_PATH"] = "config/access.example.toml"

from llm_scheduling_management_system.db import Base
from llm_scheduling_management_system.domain import models  # noqa: F401
from llm_scheduling_management_system.interfaces.http.app import create_app
from llm_scheduling_management_system.interfaces.http.dependencies import get_task_service
from llm_scheduling_management_system.services.task_service import TaskService


@pytest.fixture()
def session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(session: Session) -> Generator[TestClient, None, None]:
    app = create_app()

    def override_task_service() -> TaskService:
        return TaskService(session)

    app.dependency_overrides[get_task_service] = override_task_service

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
