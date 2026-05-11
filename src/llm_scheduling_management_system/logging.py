import sys
from pathlib import Path

from loguru import logger

from llm_scheduling_management_system.settings import settings


def configure_logging() -> None:
    log_dir = Path(settings.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / settings.log_filename

    logger.remove()

    logger.add(
        sys.stdout,
        level=settings.log_level,
        colorize=True,
        enqueue=False,
        backtrace=False,
        diagnose=False,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "{name}:{function}:{line} - "
            "<level>{message}</level>"
        ),
    )

    logger.add(
        log_path,
        level=settings.log_level,
        rotation=settings.log_rotation,
        retention=settings.log_retention,
        enqueue=False,
        backtrace=False,
        diagnose=False,
        encoding="utf-8",
        format=(
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
            "{level: <8} | "
            "{name}:{function}:{line} | "
            "{message}"
        ),
    )


__all__ = ["configure_logging", "logger"]
