import time

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.logging import logger, setup_logging
from app.routers import ghosts, locations, matching, report

# Настраивает loguru (вывод в консоль + файл backend/logs/app.log, перехват
# стандартного logging от uvicorn/sqlalchemy) — делается один раз при старте
# процесса, до создания FastAPI-приложения, чтобы даже самые ранние логи
# (например, из sqlalchemy при первом подключении к базе) шли туда же.
setup_logging()

app = FastAPI(
    title="Бюро переселения привидений",
    description="API для подбора мест переселения привидениям из старых домов.",
    version="0.1.0",
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Логирует каждый запрос и ответ — метод, путь, код ответа, время
    выполнения. Добавлено, чтобы в логе было видно сам факт того, что запрос
    вообще дошёл до backend'а (например, нажатие кнопки "Обновить
    предложения" на фронтенде должно оставить строку про
    POST /api/match/run — если её нет, значит запрос не дошёл до сервера, и
    проблема на фронтенде или в nginx, а не в бизнес-логике)."""
    started_at = time.perf_counter()
    logger.info("--> {} {}", request.method, request.url.path)
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("<-- {} {} упал с необработанным исключением", request.method, request.url.path)
        raise
    duration_ms = (time.perf_counter() - started_at) * 1000
    logger.info(
        "<-- {} {} -> {} ({:.1f} мс)", request.method, request.url.path, response.status_code, duration_ms
    )
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Единая точка отлова непойманных ошибок — фронтенд всегда получает
    понятный JSON, а не голый traceback или обрыв соединения."""
    logger.exception("Необработанная ошибка на {}", request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Что-то пошло не так на сервере бюро переселения. "
            "Мы уже записали проблему в лог — попробуйте повторить действие."
        },
    )


app.include_router(ghosts.router)
app.include_router(locations.router)
app.include_router(matching.router)
app.include_router(report.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


logger.info("Приложение «Бюро переселения привидений» проинициализировано")
