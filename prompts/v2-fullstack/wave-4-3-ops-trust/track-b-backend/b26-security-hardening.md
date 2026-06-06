# b26 · Security baseline — auth/audit/throttle (по research-отчёту)

> Трек **Backend/Data**. Против `00-CONTRACT.md` §8.9. **Владеет:** `api/core/security.py` (middleware),
> `api/core/audit.py`, документ `docs/SLO.md`; **аддитивная** регистрация middleware в `api/main.py`.
> **Модель:** 🔴 Opus — кросс-режущая безопасность (auth/audit/throttle на всех эндпоинтах), высокие ставки.
> **Волна 4.3** (AI Ops & Trust), окно 1 (backend). Демо-уровень: не ломает текущие эндпоинты (по умолчанию open в dev).

## Цель

Демо-уровневый security baseline, на который указывает research-отчёт: bearer/API-key scaffold,
audit-trail действий, rate-limit на тяжёлые эндпоинты, документ SLO/SLA. **Без ломки** текущего демо.

## Состав

- `api/core/security.py` — middleware bearer/API-key (вкл/выкл флагом `SECURITY_ENABLED`, в dev — off);
  при on — 401 без токена. Не трогает контракты ответов.
- `api/core/audit.py` — audit-trail: кто/что/когда по мутациям (`/actions`, `/copilot/chat`, tickets) →
  `output/audit.csv` (детерминированная схема, без `Date.now()` в логике — время из запроса/события).
- **Throttle/rate-limit** на тяжёлые эндпоинты (`/reports/transcribe`, `/copilot/chat`): лимит запросов
  + размер файла STT; превышение → 429 с понятным телом.
- `docs/SLO.md` — целевые latency/availability по доменам (incidents/reports/copilot), бюджеты ошибок.

## Check

- `SECURITY_ENABLED=false` (dev/демо) → все эндпоинты работают как раньше (регресс P0–P2/Волны 4 зелёный).
- `SECURITY_ENABLED=true` → запрос без токена → 401; с токеном → как обычно.
- Мутации пишут строку в `output/audit.csv`; throttle на `/copilot/chat`/STT даёт 429 при превышении.
- `docs/SLO.md` существует с целевыми latency/availability и error budget.

## Коммит (обязательно)

Заверши промпт коммитом в свою ветку — **merge на барьере берёт только коммиты**:

```bash
git add -A && git commit -m "b26: <что сделано>"
```
