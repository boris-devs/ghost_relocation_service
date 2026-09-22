# 👻 Бюро переселения привидений

Веб-приложение оператора: подбирает привидениям новое место обитания с объяснением
решения, обработкой конфликтов и ручной корректировкой.

**Стек:** FastAPI + PostgreSQL + SQLAlchemy (async) + Alembic + `uv` (backend),
чистые HTML/CSS/JS (frontend), Docker Compose + nginx (упаковка и раздача).

## Запуск

Нужен только Docker и Docker Compose.

```bash
cp .env.example .env
docker compose up --build
```

- приложение: http://localhost:8080
- API / Swagger: http://localhost:8000 / http://localhost:8000/docs

При старте `docker compose` сам поднимает Postgres, прогоняет миграции Alembic
(сервис `migrate`), заполняет базу демоданными, если она пуста (сервис `seed`), и
только потом стартует `backend` и `nginx`. Отдельного запуска без Docker нет.

После правок в `backend/*.py` пересобирайте образ (`--build`) — код копируется
в образ на этапе сборки, а не монтируется живым volume.

Остановить и стереть базу:

```bash
docker compose down -v
```

## Тесты

```bash
uv venv
uv pip install -e ".[dev]"
uv run pytest -v
```

или через Docker: `docker compose run --rm backend pytest -v`.

- `backend/tests/test_matching.py` — алгоритм подбора (без базы).
- `backend/tests/test_api.py` — API поверх SQLite в памяти.

## Структура проекта

```
pyproject.toml         # общие зависимости (uv), один на весь репозиторий
.env.example            # единый шаблон .env для Docker и локального запуска
backend/
  app/
    core/                # настройки проекта
    db/                  # ORM-модели, engine/сессия, enum'ы
    schemas/            # Pydantic-схемы запросов/ответов по сущностям
    repositories/        # доступ к данным (без бизнес-логики)
    services/             # бизнес-логика + алгоритм подбора (algorithm.py)
    routers/               # тонкие эндпоинты FastAPI
    main.py                 # сборка приложения
  seed_data/               # демоданные и точка входа сервиса seed
  alembic/                 # миграции
  tests/
frontend/
  index.html, css/, js/    # api.js, app.js, worklog-content.js (вкладка AI Worklog)
nginx/nginx.conf           # раздача frontend/ + проксирование /api/ на backend
docker-compose.yml
```

Backend разложен на три слоя: `repositories` (только доступ к данным) →
`services` (бизнес-логика, транзакции, алгоритм подбора) → `routers` (тонкий
HTTP-слой). Алгоритм в `services/algorithm.py` — чистые функции без обращения к
базе, поэтому тестируется отдельно от неё.

## Секреты

Один общий `.env` в корне (шаблон — `.env.example`), секретов в коде и образе
нет, `.env` в git не попадает.

Подробный журнал разработки (что делал человек, что — AI, найденные баги) — во
вкладке **AI Worklog** внутри самого приложения.
