# tu-security · Unit-тесты security baseline (идея #20, модуль b26)

> Трек **Tests** (`feat/tests`, окно 3). Против `00-CONTRACT.md` §8.9.
> **Модель:** 🔵 Sonnet — детерминированная проверка middleware/политик; гейт = pytest.
> **Владеет:** `api/tests/unit/test_security.py`. Инфра — из `t1`. Гонится после `b26`.

## Цель

Покрыть демо-уровневый security baseline: обратная совместимость (флаг off), auth (флаг on),
audit-trail и throttle — без сети, детерминированно.

## Состав — `api/tests/unit/test_security.py`

- `SECURITY_ENABLED=false` (демо/dev) → эндпоинты доступны как раньше (регресс P0–P2/Волны 4 не сломан).
- `SECURITY_ENABLED=true` → запрос без токена → 401; с валидным токеном → проходит.
- Мутации (`/actions`, `/copilot/chat`) пишут строку в `output/audit.csv` (детерминированная схема, без `Date.now()` в логике).
- Throttle/rate-limit на тяжёлых эндпоинтах (`/copilot/chat`, `/reports/transcribe`) → 429 при превышении лимита/размера.

## Check

- `pytest api/tests/unit/test_security.py -q` зелёный без сети.
- Флаг off → passthrough; флаг on → 401/проход; audit-строка пишется; throttle → 429.

## Коммит (обязательно)

Заверши промпт коммитом в свою ветку — **merge на барьере берёт только коммиты**:

```bash
git add -A && git commit -m "tu-security: <что сделано>"
```
