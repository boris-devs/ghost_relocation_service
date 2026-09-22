"""Общие настройки проекта. Всё читается из переменных окружения
(см. .env.example в корне репозитория) — секретов в коде нет."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ROOT_ENV_FILE = Path(__file__).resolve().parent.parent.parent.parent / ".env"


class Settings(BaseSettings):
    database_url: str = (
        "postgresql+asyncpg://ghost_reloc_service:ghost_reloc_service@db:5432/ghost_reloc_service"
    )
    environment: str = "development"
    seed_demo_data: bool = True
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=str(_ROOT_ENV_FILE), extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
