"""Роутер Fleet Copilot (b21, §8.3) — `POST /api/copilot/chat`.

Авто-discovery в `api/main.py:_discover_routers()` подключает модуль по объекту
`router` — общий `api/routers/__init__.py` НЕ правим (иначе кросс-трек гонка).
Роутер ничего не считает: проверяет feature-flag и делегирует `copilot_service.chat`.
"""

from __future__ import annotations

from typing import Annotated

import duckdb
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.core.ai_flags import FeatureDisabledResponse, flags
from api.core.duckdb_conn import get_db
from api.services import copilot_service
from api.services.copilot_service import CopilotMessage

router = APIRouter(prefix="/api/copilot", tags=["copilot"])

DbDep = Annotated[duckdb.DuckDBPyConnection, Depends(get_db)]


class ChatRequest(BaseModel):
    """Тело `POST /api/copilot/chat` (§8.4): свободный запрос RU/EN + опц. язык."""

    text: str
    lang: str | None = None


@router.post("/chat", response_model=None)
def chat(body: ChatRequest, db: DbDep) -> CopilotMessage | FeatureDisabledResponse:
    """Свободный запрос → выбор инструмента → `CopilotMessage` (§8.4).

    Флаг `copilot` выкл → 200 «feature disabled» (§8.6, не 5xx). Без `GROQ_API_KEY`
    сервис детерминированно уходит в фолбэк. Мусор/пустой ввод → вежливый дефолт.
    """
    if not flags.is_enabled("copilot"):
        return FeatureDisabledResponse(detail="copilot feature disabled")
    return copilot_service.chat(body.text, body.lang, db)
