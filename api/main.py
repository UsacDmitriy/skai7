"""
FastAPI application entry point.

Run locally:
    uvicorn api.main:app --reload

Only the app skeleton + infrastructure live here. Routers are wired in x2/b6.
"""
from __future__ import annotations

import importlib
import logging
import pkgutil
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

import api.routers as routers_pkg
from api.core.config import settings
from api.core.duckdb_conn import close_connection

logger = logging.getLogger("skai.api")


def _discover_routers() -> list[APIRouter]:
    """Авто-обход пакета `api.routers`: каждый модуль с объектом `router`
    подключается без правки общего списка (P0 от b6 + P1/P2 от b11–b13).
    """
    discovered: list[APIRouter] = []
    for _, name, _ in pkgutil.iter_modules(routers_pkg.__path__):
        mod = importlib.import_module(f"api.routers.{name}")
        router = getattr(mod, "router", None)
        if isinstance(router, APIRouter):
            discovered.append(router)
    return discovered


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown: warn if the DuckDB file is missing, close conn on exit."""
    if not settings.db_path.exists():
        logger.warning(
            "DuckDB не найден: %s. Запусти `make db` для сборки базы.",
            settings.db_path,
        )
    else:
        logger.info("DuckDB найден: %s", settings.db_path)
    yield
    close_connection()


def create_app() -> FastAPI:
    app = FastAPI(title="SKAI API", version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    routers = _discover_routers()
    for router in routers:
        app.include_router(router)
    logger.info("Подключено роутеров: %d", len(routers))

    return app


app = create_app()
