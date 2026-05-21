from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """系统全局配置模型。

    用途:
        用于加载、解析并存储系统的基础运行配置（如应用名称、环境、调试状态、时区、数据库 URL、日志级别和路径等）。
        支持自动从环境变量或 `.env` 文件读取带有 `LSMS_` 前缀的配置项。

    用法:
        直接导入已实例化的 `settings` 对象使用其属性，如 `settings.database_url`。

    @Author: mosliu
    """
    app_name: str = "llm-scheduling-management-system"
    app_env: str = "local"
    debug: bool = True
    timezone: str = "Asia/Shanghai"
    database_url: str = Field(default="sqlite:///./data/app.db")
    log_level: str = "INFO"
    log_dir: str = "logs"
    log_filename: str = "app.log"
    log_rotation: str = "00:00"
    log_retention: str = "14 days"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="LSMS_",
        extra="ignore",
    )

    @property
    def database_path(self) -> Path | None:
        """获取 SQLite 数据库文件的具体本地路径。

        用途:
            从 `database_url` 中解析出 SQLite 本地文件路径。如果不是以 `sqlite:///` 开头的 URL，则返回 None。

        用法:
            path = settings.database_path

        返回:
            Path | None: SQLite 文件的 Path 对象，非 SQLite 数据库则返回 None。

        @Author: mosliu
        """
        prefix = "sqlite:///"
        if self.database_url.startswith(prefix):
            raw_path = self.database_url[len(prefix) :]
            return Path(raw_path)
        return None


settings = Settings()
