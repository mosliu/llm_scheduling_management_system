from collections.abc import Generator
from pathlib import Path

from sqlalchemy import Text, create_engine, text
from sqlalchemy.dialects import mysql
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.sql.sqltypes import Text as TextType

from llm_scheduling_management_system.settings import settings

MYSQL_UTF8MB4_CHARSET = "utf8mb4"
MYSQL_UTF8MB4_COLLATION = "utf8mb4_unicode_ci"


class Base(DeclarativeBase):
    """SQLAlchemy 声明式模型基类。

    用途:
        所有数据库映射实体模型的父类，供 SQLAlchemy 收集表结构元数据。

    用法:
        直接继承自该类并定义类属性映射到数据库字段。

    @Author: mosliu
    """
    __abstract__ = True
    __table_args__ = {
        "mysql_charset": MYSQL_UTF8MB4_CHARSET,
        "mysql_collate": MYSQL_UTF8MB4_COLLATION,
    }
    pass


def utf8mb4_longtext() -> Text:
    """Return a cross-dialect long text type with utf8mb4 on MySQL.

    MySQL's regular TEXT is limited to 64 KiB and inherits table charset. Workflow
    artifacts and fetched documents can be hundreds of kilobytes and may contain
    Chinese or supplementary-plane Unicode characters, so MySQL needs LONGTEXT
    plus utf8mb4 explicitly.
    """
    return Text().with_variant(
        mysql.LONGTEXT(charset=MYSQL_UTF8MB4_CHARSET, collation=MYSQL_UTF8MB4_COLLATION),
        "mysql",
    )


def normalize_database_url(database_url: str) -> str:
    """Normalize DB driver defaults required by the application.

    The configured value stays the source of truth, but MySQL/MariaDB connections
    must always negotiate utf8mb4 or external Unicode content can fail at insert
    time even when Python strings are valid.
    """
    url = make_url(database_url)
    if url.get_backend_name() in {"mysql", "mariadb"}:
        query = dict(url.query)
        query["charset"] = MYSQL_UTF8MB4_CHARSET
        url = url.set(query=query)
    return url.render_as_string(hide_password=False)


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

database_url = normalize_database_url(settings.database_url)

engine = create_engine(
    database_url,
    future=True,
    echo=False,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args={"check_same_thread": False} if database_url.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)


def _quote_mysql_identifier(identifier: str) -> str:
    return f"`{identifier.replace('`', '``')}`"


def _mysql_text_columns_from_metadata() -> dict[str, list[tuple[str, bool]]]:
    text_columns: dict[str, list[tuple[str, bool]]] = {}
    for table in Base.metadata.sorted_tables:
        columns = [
            (column.name, column.nullable)
            for column in table.columns
            if isinstance(column.type, TextType)
        ]
        if columns:
            text_columns[table.name] = columns
    return text_columns


def ensure_mysql_utf8mb4_schema(bind: Engine) -> None:
    """Repair legacy MySQL table/column charset drift.

    `create_all()` is intentionally additive and does not rewrite existing
    columns. This guard keeps long-running API/worker services from repeatedly
    crashing when older MySQL tables were created with latin1/utf8mb3 defaults or
    with 64 KiB TEXT columns.
    """
    if bind.dialect.name not in {"mysql", "mariadb"}:
        return

    text_columns_by_table = _mysql_text_columns_from_metadata()
    if not text_columns_by_table:
        return

    with bind.begin() as connection:
        database_name = connection.execute(text("SELECT DATABASE()")).scalar_one_or_none()
        if not database_name:
            return

        existing_tables = set(
            connection.execute(
                text(
                    """
                    SELECT TABLE_NAME
                    FROM information_schema.TABLES
                    WHERE TABLE_SCHEMA = :schema_name
                    """
                ),
                {"schema_name": database_name},
            ).scalars()
        )

        for table_name, text_columns in text_columns_by_table.items():
            if table_name not in existing_tables:
                continue

            table_collation = connection.execute(
                text(
                    """
                    SELECT TABLE_COLLATION
                    FROM information_schema.TABLES
                    WHERE TABLE_SCHEMA = :schema_name AND TABLE_NAME = :table_name
                    """
                ),
                {"schema_name": database_name, "table_name": table_name},
            ).scalar_one_or_none()
            quoted_table = _quote_mysql_identifier(table_name)
            if not str(table_collation or "").startswith(MYSQL_UTF8MB4_CHARSET):
                connection.execute(
                    text(
                        f"ALTER TABLE {quoted_table} "
                        f"DEFAULT CHARACTER SET {MYSQL_UTF8MB4_CHARSET} "
                        f"COLLATE {MYSQL_UTF8MB4_COLLATION}"
                    )
                )

            column_rows = connection.execute(
                text(
                    """
                    SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_SET_NAME, COLLATION_NAME
                    FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA = :schema_name AND TABLE_NAME = :table_name
                    """
                ),
                {"schema_name": database_name, "table_name": table_name},
            ).mappings()
            column_info = {row["COLUMN_NAME"]: row for row in column_rows}

            for column_name, nullable in text_columns:
                row = column_info.get(column_name)
                if row is None:
                    continue
                needs_longtext = str(row["DATA_TYPE"]).lower() != "longtext"
                needs_charset = row["CHARACTER_SET_NAME"] != MYSQL_UTF8MB4_CHARSET
                needs_collation = not str(row["COLLATION_NAME"] or "").startswith(MYSQL_UTF8MB4_CHARSET)
                if not (needs_longtext or needs_charset or needs_collation):
                    continue
                null_sql = "NULL" if nullable else "NOT NULL"
                connection.execute(
                    text(
                        f"ALTER TABLE {quoted_table} MODIFY {_quote_mysql_identifier(column_name)} "
                        f"LONGTEXT CHARACTER SET {MYSQL_UTF8MB4_CHARSET} "
                        f"COLLATE {MYSQL_UTF8MB4_COLLATION} {null_sql}"
                    )
                )


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
    ensure_mysql_utf8mb4_schema(engine)


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
