import sys
from pathlib import Path

from loguru import logger

from llm_scheduling_management_system.settings import settings


def configure_logging() -> None:
    """配置系统的全局日志系统。

    用途:
        使用 Loguru 创建和配置日志记录器，将其输出同时重定向至控制台（sys.stdout）和指定的本地日志文件。
        控制台输出支持彩色格式；文件输出支持自动日志文件切割（rotation）和归档保留（retention）。

    用法:
        在系统初始化或入口文件（如 FastAPPI app、CLI 工具等）最早阶段调用该函数。

    @Author: mosliu
    """
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
