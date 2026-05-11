from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
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
        prefix = "sqlite:///"
        if self.database_url.startswith(prefix):
            raw_path = self.database_url[len(prefix) :]
            return Path(raw_path)
        return None


settings = Settings()
