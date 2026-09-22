"""Точка входа одноразового сервиса `seed` в docker-compose: проверяет, есть ли
уже данные в базе, и заполняет её демонстрационными данными, только если её нет.
Не запускается при каждом старте backend'а — это отдельный шаг, как и миграции."""

import asyncio
import logging

from app.core.config import get_settings
from app.db.session import async_session_factory

from .seed import seed_if_empty

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ghost_reloc_service.seed")


async def main() -> None:
    settings = get_settings()
    if not settings.seed_demo_data:
        logger.info("SEED_DEMO_DATA=false — пропускаем заполнение демонстрационными данными.")
        return

    async with async_session_factory() as session:
        await seed_if_empty(session)
        await session.commit()
    logger.info("Проверка демонстрационных данных завершена.")


if __name__ == "__main__":
    asyncio.run(main())
