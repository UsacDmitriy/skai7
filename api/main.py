"""
FastAPI application entry point.

Run locally:
    uvicorn api.main:app --reload

Only the app skeleton + infrastructure live here. Routers are wired in x2/b6.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.core.config import settings
from api.core.duckdb_conn import close_connection

logger = logging.getLogger("skai.api")


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

    # routers подключаются в x2/b6

    return app


app = create_app()
