# x3 · Сквозной smoke + тесты

> **Барьер-волна, финал.** **Владеет:** только запуск/проверки (smoke). Авторство тестов делегировано
> Codex-задачам `prompts/codex-tasks/T1–T3` (`api/tests/**`, `web/**/*.test.tsx`). Ничего не переписывает —
> при провале заводит дефект для соответствующего трека.

## Перед стартом

В окне `skai_7` на ветке `integration` (после x2). **`main` всё ещё стабилен** — продвинем его только в финале, если smoke зелёный.

## Проверка предыдущего шага (x2 · склейка)

Не запускай сквозной smoke, пока не подтвердишь результат x2:

- `make db && make api` → `GET /api/incidents` 200, `GET /api/health` ok.
- `make web` → :5173, запросы `/api/...` проксируются на :8000 без CORS-ошибок.
- Карточка инцидента грузится с живого бэка (без фикстур).

Не прошло — вернись к x2.

## Цель

Подтвердить, что стек работает end-to-end по сквозному домену incidents и что заглушки на месте.

## Шаги

### Данные/бэкенд
1. `make db` → сводка: `video_events__selected_video_alarms`=54, `alarm_type_catalog`=14, view `v_incidents`=54.
2. `make api`, затем:
   - `GET /api/health` → 200.
   - `GET /api/incidents` → 200, массив `IncidentSummary`, поля `risk_score`(int), `driver`, `vehicle_model` **заполнены** (обогащение работает, не NULL).
   - `GET /api/incidents/{id}` → 200 `IncidentDetail` с `cameras[]`, `telemetry[]`, `evidence_summary`, `speed_limit_kmh`, `is_night`.
   - `GET /api/incidents/{id}/video/5` → 200 mp4 (для DMS-алярма с видео) либо 404 (без).
   - `GET /api/fuel/...` → 501.
   - `POST /api/actions` → 200, строка появилась в `output/actions.csv`.
3. OpenAPI `/docs` открывается, все теги (incidents/reports/vehicles/actions/fuel/sensors/navigation) видны.

### pytest (`api/tests/`)
- `test_enrichment.py` (от b2) — детерминизм, диапазоны risk_score.
- `test_incidents_api.py` — `TestClient`: список, деталь, 404 на несуществующий id, 501 на fuel.

### Фронт
4. `make web`, открыть `/incidents/<id>`:
   - на живом API карточка показывает видео/телеметрию/score;
   - кейс «нет видео» → пустое состояние + «Запросить архив»;
   - `/monitor` и `/report` открываются (scaffold);
   - действия пишутся, статус меняется.
5. `cd web && npm run typecheck` — без ошибок (типы совпадают с контрактом).

## Критерии приёмки

- Сквозной домен incidents проходит ETL→enrichment→view→repo→service→router→client→экран.
- Обогащение видно в ответах API (driver/model/risk_score не пустые).
- Streamlit отсутствует (`grep -r "import streamlit"` пусто).
- Заглушки fuel/sensors/navigation отвечают 501; таблицы в DuckDB существуют.

## Финализация — продвинуть main (P0 стабилен)

**Только если все критерии приёмки выше зелёные**, зафиксируй стабильный P0 в `main`:

```bash
git -C /Users/dimausac/projects/skai_7 checkout main
git merge --ff-only integration       # main догоняет integration (fast-forward, без новых коммитов)
git checkout integration              # вернуться на integration для волны 2
```

Smoke красный → **`main` НЕ трогаем**, заводим дефект трека и чиним на `integration`. Так `main` всегда = последний зелёный P0.
