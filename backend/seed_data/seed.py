"""Демонстрационные данные — покрывают все обязательные сценарии из ТЗ:
обычный подбор, заявку без подходящего места, переполненное место,
просроченный дедлайн (для ручного конфликта на фронтенде) и т.д."""

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Ghost, Location


async def seed_if_empty(session: AsyncSession) -> None:
    existing = await session.execute(select(Location.id).limit(1))
    if existing.first() is not None:
        return  

    TODAY = date.today()

    locations = [
        Location(
            name="Старый замок на холме",
            location_type="замок",
            capacity=5,
            occupied=1,
            lighting="dim",
            noise_level=2,
            humidity="normal",
            ambient_temperature=12,
            has_people=False,
            has_mirrors=True,
            has_attic=True,
            restrictions=[],
        ),
        Location(
            name="Маяк на мысе Туманный",
            location_type="маяк",
            capacity=2,
            occupied=0,
            lighting="bright",
            noise_level=4,
            humidity="damp",
            ambient_temperature=8,
            has_people=True,
            has_mirrors=False,
            has_attic=False,
            restrictions=[],
        ),
        Location(
            name="Городская библиотека",
            location_type="библиотека",
            capacity=3,
            occupied=3,  
            lighting="dim",
            noise_level=1,
            humidity="dry",
            ambient_temperature=19,
            has_people=True,
            has_mirrors=False,
            has_attic=False,
            restrictions=[],
        ),
        Location(
            name="Заброшенный театр",
            location_type="театр",
            capacity=4,
            occupied=1,
            lighting="dark",
            noise_level=3,
            humidity="normal",
            ambient_temperature=15,
            has_people=False,
            has_mirrors=True,
            has_attic=False,
            restrictions=[],
        ),
        Location(
            name="Подвал старой типографии",
            location_type="подвал",
            capacity=6,
            occupied=0,
            lighting="dark",
            noise_level=0,
            humidity="damp",
            ambient_temperature=10,
            has_people=False,
            has_mirrors=False,
            has_attic=False,
            restrictions=[],
        ),
    ]
    session.add_all(locations)
    await session.flush()

    ghosts = [
        Ghost(
            name="Агата Сумеречная",
            anxiety_level=8,
            favorite_temperature=10,
            relocation_deadline=TODAY + timedelta(days=14),
            special_conditions=["needs_silence", "likes_dampness"],
        ),
        Ghost(
            name="Барон фон Скрип",
            anxiety_level=3,
            favorite_temperature=13,
            relocation_deadline=TODAY + timedelta(days=30),
            special_conditions=["needs_attic", "fears_mirrors"],  
        ),
        Ghost(
            name="Тихая Мельника",
            anxiety_level=6,
            favorite_temperature=9,
            relocation_deadline=TODAY + timedelta(days=7),
            special_conditions=["no_humans_nearby", "needs_darkness"],
        ),
        Ghost(
            name="Эхо Библиотекарь",
            anxiety_level=4,
            favorite_temperature=19,
            relocation_deadline=TODAY + timedelta(days=5),
            special_conditions=[],  
        ),
        Ghost(
            name="Просрочка Забытый",
            anxiety_level=5,
            favorite_temperature=14,
            relocation_deadline=TODAY - timedelta(days=2),  
            special_conditions=[],
        ),
        Ghost(
            name="Сырой Игнат",
            anxiety_level=2,
            favorite_temperature=10,
            relocation_deadline=TODAY + timedelta(days=60),
            special_conditions=["likes_dampness", "dislikes_crowds"],
        ),
    ]
    session.add_all(ghosts)
    await session.flush()
