"""Audit-trail действий (b26 · §8.9).

Кто/что/когда по мутациям (`/api/actions`, `/api/copilot/chat`, `/api/tickets`)
дописывается строкой в `output/audit.csv`. Схема СОВПАДАЕТ с governance-логом копилота
(`api/services/copilot_service.py:_audit`), чтобы файл оставался однородным:

    ts,event,feature,tool,lang,source,args

Контракт:
- **best-effort** — любой сбой логирования глотается; аудит не часть ответа и не
  должен ронять запрос (`record` никогда не бросает);
- **детерминированная схема** — порядок и состав колонок фиксированы (`AUDIT_HEADER`);
- **время из события** — `ts` приходит снаружи (момент запроса). Без `Date.now()`
  в бизнес-логике: дефолт берётся один раз здесь, а вызывающий код (middleware)
  стампит время приёма запроса и передаёт его явно.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone

from api.core.config import settings

# Канон схемы — единый с копилотом (см. copilot_service._AUDIT_HEADER).
AUDIT_HEADER = ["ts", "event", "feature", "tool", "lang", "source", "args"]


def now_iso() -> str:
    """Текущее UTC-время в ISO-8601 (стамп события на приёме запроса)."""
    return datetime.now(timezone.utc).isoformat()


def record(
    event: str,
    feature: str,
    *,
    tool: str = "",
    lang: str = "",
    source: str = "api",
    args: dict | None = None,
    ts: str | None = None,
) -> None:
    """Дописать строку аудита в `output/audit.csv`. Никогда не бросает.

    Args:
        event:   тип события, напр. `mutation` / `action_recorded`.
        feature: домен — `actions` / `copilot` / `tickets`.
        tool:    уточнение (метод+путь или имя действия).
        lang:    язык запроса, если применимо.
        source:  откуда инициировано (`api` для HTTP-мутаций).
        args:    короткий контекст (путь, статус) — сериализуется в JSON.
        ts:      ISO-время события; если None — берётся `now_iso()`.
    """
    try:
        path = settings.output_dir / "audit.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        is_new = not path.exists()
        with path.open("a", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            if is_new:
                writer.writerow(AUDIT_HEADER)
            writer.writerow([
                ts or now_iso(),
                event,
                feature,
                tool,
                lang,
                source,
                json.dumps(args or {}, ensure_ascii=False),
            ])
    except Exception:
        # Аудит — сайд-эффект: его падение не должно влиять на ответ эндпоинта.
        pass
