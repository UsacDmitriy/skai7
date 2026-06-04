# x3 · Сквозной smoke + тесты

> **Барьер-волна, финал.** **Владеет:** только запуск/проверки (smoke). Авторство тестов делегировано
> Codex-задачам `prompts/codex-tasks/T1–T3` (`api/tests/**`, `web/**/*.test.tsx`). Ничего не переписывает —
> при провале заводит дефект для соответствующего трека.

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
