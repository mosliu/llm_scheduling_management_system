from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from llm_scheduling_management_system.settings import settings


class Base(DeclarativeBase):
    """SQLAlchemy 声明式模型基类。

    用途:
        所有数据库映射实体模型的父类，供 SQLAlchemy 收集表结构元数据。

    用法:
        直接继承自该类并定义类属性映射到数据库字段。

    @Author: mosliu
    """
    pass


def _ensure_sqlite_parent_exists() -> None:
    """确保 SQLite 数据库文件父目录存在。

    用途:
        若配置为 SQLite 数据库文件，则检查其上级目录是否存在；若不存在则自动递归创建。

    用法:
        模块加载时自动调用。

    @Author: mosliu
    """
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
    """初始化数据库。

    用途:
        导入所有的数据库实体模型，并在数据库中创建所有不存在的表结构。

    用法:
        在系统启动脚本或引导流程中调用该函数完成数据库表的初始化建表工作。

    @Author: mosliu
    """
    # Import models here so SQLAlchemy metadata is populated before create_all runs.
    from llm_scheduling_management_system.domain import models  # noqa: F401

    Base.metadata.create_all(bind=engine)


def get_db_session() -> Generator[Session, None, None]:
    """获取数据库会话生成器。

    用途:
        创建并产生一个 SQLAlchemy Session 实例，用于数据库事务操作，并在操作结束后自动关闭会话释放资源。

    用法:
        多用于 FastAPI 的依赖注入：Depends(get_db_session)，或者在 context manager 中使用。

    返回:
        Generator[Session, None, None]: 数据库会话迭代器。

    @Author: mosliu
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
