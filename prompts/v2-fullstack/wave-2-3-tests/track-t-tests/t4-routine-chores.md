# T4 · Рутинные мелкие задачи (граббэг)

> Track T (Claude Code, `feat/tests`). Мелкие самодостаточные правки, каждый пункт независим —
> **Модель:** 🟢 Qwen 3.7 max — механическая транскрипция против точной спеки; гейт ловит ошибку.
> бери по одному. Против `00-CONTRACT.md`. Не пересекается с продуктовыми треками по ключевым файлам.

## Задачи (выполнять по одной, каждая = отдельный коммит)

1. **`.env.example`** (корень) — `GROQ_API_KEY=`, `WHISPER_MODEL=large-v3`, `WHISPER_DEVICE=cpu`,
   `VITE_API_BASE=/api`, `VITE_API_TARGET=http://localhost:8000`, `VITE_USE_FIXTURES=false`. + строка в README про копирование.

2. **Линт/формат бэка** — `api/pyproject.toml` или `ruff.toml`: ruff + правила; `make lint` цель (дополнить Makefile только при наличии, иначе TODO для x2).

3. **Линт/формат фронта** — `web/.eslintrc` + `web/.prettierrc` (если не созданы f1); скрипты `lint`/`format` в `web/package.json` (добавить, не ломая существующие).

4. **OpenAPI-экспорт** — `scripts/export_openapi.py`: поднять `api.main:app`, выгрузить `openapi.json` в `docs/`.
   Цель `make openapi` (или standalone). Полезно для документации/клиентов.

5. **Run-документация** — `docs/RUNBOOK.md`: пошагово `make install → make db → make api + make web`,
   переменные окружения, где лежат seed/данные, как прогнать тесты (T1–T3), типичные ошибки.

6. **Fixtures-sync** — `scripts/gen_fixtures.py`: из `data/mock/incidents.py` сгенерировать/обновить
   `web/src/api/fixtures.ts` (форма по §3.1/§7.5), чтобы фронт-фикстуры не расходились с моком. (Согласовать с f3.)

7. **CI-проверка локально** — `scripts/check.sh`: `ruff` + `pytest -q` + `cd web && npm run typecheck && npx vitest run`.
   Один вход для «всё зелёное» перед коммитом.

8. **pre-commit** (опц.) — `.pre-commit-config.yaml`: ruff + prettier на изменённые файлы.

## Check (per задача)
- Изменение затрагивает только свой вспомогательный файл; продуктовый код не тронут.
- `scripts/check.sh` (после п.7) проходит на текущем состоянии репозитория.
