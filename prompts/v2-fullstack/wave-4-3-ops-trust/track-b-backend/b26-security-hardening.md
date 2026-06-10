# b26 · Security baseline — auth/audit/throttle (по research-отчёту)

> Трек **Backend/Data**. Против `00-CONTRACT.md` §8.9. **Владеет:** `api/core/security.py` (middleware),
> `api/core/audit.py`, документ `docs/SLO.md`; **аддитивная** регистрация middleware в `api/main.py`.
> **Модель:** 🔴 Opus — кросс-режущая безопасность (auth/audit/throttle на всех эндпоинтах), высокие ставки.
> **Волна 4.3** (AI Ops & Trust), окно 1 (backend). Демо-уровень: не ломает текущие эндпоинты (по умолчанию open в dev).

## Цель

Демо-уровневый security baseline, на который указывает research-отчёт: bearer/API-key scaffold,
audit-trail действий, rate-limit на тяжёлые эндпоинты, документ SLO/SLA. **Без ломки** текущего демо.

## Состав

- `api/core/security.py` — middleware bearer/API-key; при on — 401 без токена. Не трогает контракты ответов.
  - **Дом флага (обязательно):** поле `security_enabled: bool = False` в `Settings`
    (`api/core/config.py`, pydantic-settings, `env_prefix="SKAI_"` → env-переменная
    **`SKAI_SECURITY_ENABLED`**; голая `SECURITY_ENABLED` процессом НЕ читается).
  - Middleware читает `settings.security_enabled` (не кэшировать значение на импорте модуля);
    при `False` — полный no-op (ветка 401 недостижима).
  - **Гарантия blast-radius:** при дефолте `False` ни один существующий эндпоинт/тест
    P0–P2/Волн 3–4 не меняет поведение.
- `api/core/audit.py` — audit-trail: кто/что/когда по мутациям (`/actions`, `/copilot/chat`, tickets) →
  `output/audit.csv` (детерминированная схема, без `Date.now()` в логике — время из запроса/события).
- **Throttle/rate-limit** на тяжёлые эндпоинты (`/reports/transcribe`, `/copilot/chat`): лимит запросов
  + размер файла STT; превышение → 429 с понятным телом.
- `docs/SLO.md` — целевые latency/availability по доменам (incidents/reports/copilot), бюджеты ошибок.

## Check

- `python -c "from api.core.config import settings; assert settings.security_enabled is False"` — дефолт off доказан.
- Флаг читается на **СТАРТЕ процесса сервера** (env на curl не действует):
  `SKAI_SECURITY_ENABLED=true make api` → запрос без токена → 401, с токеном → как обычно;
  перезапуск без env → все эндпоинты как раньше (регресс P0–P2/Волн 3–4 зелёный).
- `pytest api/tests/unit -q` зелёный на дефолтных настройках (security off).
- Мутации пишут строку в `output/audit.csv`; throttle на `/copilot/chat`/STT даёт 429 при превышении.
- `docs/SLO.md` существует с целевыми latency/availability и error budget.

## Коммит (обязательно)

Заверши промпт коммитом в свою ветку — **merge на барьере берёт только коммиты**:

```bash
# параллельно в одном worktree — стейджи только свои файлы (НЕ git add -A)
git add api/core/security.py api/core/audit.py docs/SLO.md api/main.py api/core/config.py
git commit -m "b26: <что сделано>"
```
