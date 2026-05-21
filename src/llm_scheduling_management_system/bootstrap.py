from pathlib import Path

from llm_scheduling_management_system.db import Base, engine, init_db
from llm_scheduling_management_system.logging import logger
from llm_scheduling_management_system.settings import settings


def reset_local_database() -> None:
    """重置本地SQLite数据库。

    用途:
        清除本地数据库中所有的表、断开引擎连接，删除原有的SQLite数据库文件，并重新初始化数据库表结构。

    用法:
        直接调用该函数即可重置当前系统配置的本地数据库文件。

    @Author: mosliu
    """
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
    """确保本地数据库已初始化。

    用途:
        检查并初始化本地数据库。若数据库结构不存在，则会建表。

    用法:
        在系统启动或服务初始化时调用，确保数据库可访问。

    返回:
        Path | None: 本地数据库文件的路径，如果不使用文件数据库则返回 None。

    @Author: mosliu
    """
    init_db()
    logger.info("Ensured local database exists")
    return settings.database_path
