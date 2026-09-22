"""Единая настройка логирования на весь backend через loguru.

Раньше использовался стандартный модуль `logging` (`logging.getLogger(...)`) —
его вывод легко потерять среди служебных логов uvicorn, и в нём не видно,
что реально произошло внутри бизнес-логики (например, сколько заявок было
сохранено при подборе). Эта настройка:

1. Перехватывает стандартный `logging` (в том числе логи uvicorn/uvicorn.access
   и SQLAlchemy) и пропускает его через loguru, чтобы весь вывод был в одном
   формате и в одном месте.
2. Пишет в stdout (виден в `docker compose logs backend`) и одновременно в файл
   `backend/logs/app.log` с ротацией — так лог не теряется между перезапусками
   контейнера и его можно открыть и почитать отдельно от терминала.
3. Даёт остальному коду проекта единый `from app.core.logging import logger`.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from loguru import logger

from app.core.config import get_settings

_LOG_DIR = Path(__file__).resolve().parent.parent.parent / "logs"
_LOG_FILE = _LOG_DIR / "app.log"

_LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)


class _InterceptHandler(logging.Handler):
    """Перенаправляет записи стандартного logging (uvicorn, sqlalchemy, ...)
    в loguru, чтобы не было двух параллельных, по-разному отформатированных
    источников логов."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def setup_logging() -> None:
    """Вызывается один раз при старте приложения (см. app.main)."""
    settings = get_settings()

    logger.remove()
    logger.add(sys.stdout, format=_LOG_FORMAT, level=settings.log_level, colorize=True, backtrace=True, diagnose=False)

    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger.add(
        _LOG_FILE,
        format=_LOG_FORMAT,
        level=settings.log_level,
        rotation="5 MB",
        retention=5,
        encoding="utf-8",
        backtrace=True,
        diagnose=False,
    )

    logging.basicConfig(handlers=[_InterceptHandler()], level=0, force=True)
    for noisy_logger in ("uvicorn", "uvicorn.error", "uvicorn.access", "sqlalchemy.engine"):
        logging.getLogger(noisy_logger).handlers = [_InterceptHandler()]
        logging.getLogger(noisy_logger).propagate = False

    logger.info("Логирование настроено (уровень {}), файл лога: {}", settings.log_level, _LOG_FILE)
