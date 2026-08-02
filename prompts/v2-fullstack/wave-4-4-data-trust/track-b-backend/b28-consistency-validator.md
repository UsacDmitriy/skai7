# b28 · Валидатор консистентности данных (фича #22, владелец §10.1/§10.3-часть 1)

> Трек **Backend/Data**. Против `00-CONTRACT.md` §10.0–§10.3, §10.5. **Владеет:** `api/sql/34_v_consistency.sql`,
> `api/services/consistency_service.py`, `api/domain/consistency.py`, роутер `api/routers/consistency.py`
> (автодискавери `api/main.py:_discover_routers` — НЕ редактируй общий `api/routers/__init__.py`).
> **Исполнение:** bounded ClinePass package; role `worker`; route category `code`; exact route/model only from `tools/clinepass-mcp/models.env` — детерминированный SQL/агрегация против контракта; гейт = Check + tu-consistency.
> **Волна 4.4**, окно 1 (backend), **первый** (затем b29). Зависит от: b1 (ETL/таблицы), §10.

## Цель

`GET /api/consistency` → `ConsistencyReport` (§10.2): 7 детерминированных кросс-датасетных проверок
целостности + сводные `evidence_rate`/`speed_agreement_rate`. Это слой доверия к данным
(кейсы Фомина/Маслова), НЕ AI-фича: без сети, без `ai_flags`/`AiFeatureState`.

## Состав

- `api/sql/34_v_consistency.sql` — view `v_consistency_checks` (строка на проверку:
  `check_id, affected_count, total`), по CTE на проверку. Идемпотентно (`CREATE OR REPLACE VIEW`).
  Таблица проверок — **точно по §10.3**:

| check_id | Таблицы | SQL-идея |
|---|---|---|
| `video_fleet_no_track` | `video_events__selected_video_alarms`, `video_events__track_points` | `"UnitStateNumber"` без строк в track_points (`unit_state_number`) |
| `incident_no_video` | alarms, `video_events__video_files` | `"VideoCount" > 0` и нет строк в video_files по `alarm_id` |
| `terminal_duplication` | alarms | `"UnitStateNumber"` с `COUNT(DISTINCT "TerminalId") > 1` |
| `plate_match_coverage` | `reference__vehicle_matches` | `match_status <> 'matched'` по каждому `source_list` |
| `timestamp_monotonicity` | track_points | `alarm_id`, где `timestamp_utc` убывает при росте `point_index` |
| `coordinate_sanity` | alarms, track_points | NULL/пустые/вне ±90/±180/(0,0) координаты |
| `speed_disagreement` | `v_speed_check` (b29) | `agreement='major'`; **до b29 view нет** → CTE-заглушка `0/0` с комментарием `-- b29 заменяет` |

  Пример CTE (формат для остальных шести):

  ```sql
  incident_no_video AS (
    SELECT 'incident_no_video' AS check_id,
           COUNT(*) FILTER (WHERE vf.alarm_id IS NULL) AS affected_count,
           COUNT(*) AS total
    FROM video_events__selected_video_alarms a
    LEFT JOIN (SELECT DISTINCT alarm_id FROM video_events__video_files) vf
      ON CAST(a."AlarmId" AS VARCHAR) = CAST(vf.alarm_id AS VARCHAR)
    WHERE CAST(a."VideoCount" AS INTEGER) > 0
  )
  ```

- `consistency_service.report() -> ConsistencyReport`:
  - читает `v_consistency_checks`; **статусы считает сервис, не SQL** (§10.2): `fail` ratio>0.2 ·
    `warn` ratio>0 · `ok`; `ratio = affected/total`, при `total=0` → `0.0`;
  - `sample_ids` (≤5) — отдельными лёгкими запросами по каждой проверке (id аларма/госномер);
  - `title_ru`/`description_ru` — фиксированный словарь в коде (детерминизм);
  - `evidence_rate = 1 − ratio(incident_no_video)`; `speed_agreement_rate = 1 − ratio(speed_disagreement)`.
- `api/domain/consistency.py` — Pydantic-схемы `ConsistencyCheck`/`ConsistencyReport` **дословно по §10.2**.
  Пример одного элемента ответа:

  ```json
  {
    "check_id": "terminal_duplication",
    "title_ru": "Дубли терминалов на ТС",
    "status": "warn",
    "affected_count": 2,
    "total": 21,
    "ratio": 0.0952,
    "sample_ids": ["О577ТС178", "Т780РН198"],
    "description_ru": "ТС с более чем одним TerminalId — источник дублей на карте (кейс Балтики)"
  }
  ```

- Роутер `GET /api/consistency`; файл `api/routers/consistency.py` с **модульным** `router = APIRouter(...)`.

## Check

- `make db` → view создан; `python -c "import duckdb; c=duckdb.connect('data/skai.duckdb'); print(c.sql('select * from v_consistency_checks').fetchall())"` — 7 строк.
- `curl -s localhost:8000/api/consistency | jq -e '.checks|length==7'`.
- `curl -s localhost:8000/openapi.json | jq -e '.paths."/api/consistency"'` — роутер подхвачен автодискавери
  (иначе тихий 404 — прецедент scene-эндпоинта).
- `jq -e '[.checks[].ratio]|all(.>=0 and .<=1)'`; `evidence_rate`/`speed_agreement_rate` ∈ [0,1].
- Детерминизм: `diff <(curl -s localhost:8000/api/consistency) <(curl -s localhost:8000/api/consistency)` пуст.
- `pytest api/tests/unit -q` зелёный (регресс не сломан); `coordinate_sanity` находит реально существующие
  пустые координаты в alarms (affected_count > 0).

## Коммит (обязательно)

Заверши промпт коммитом в свою ветку — **merge на барьере берёт только коммиты**:

```bash
# стейджи только свои файлы (НЕ git add -A)
git add api/sql/34_v_consistency.sql api/services/consistency_service.py api/routers/consistency.py api/domain/consistency.py
git commit -m "b28: валидатор консистентности — 7 проверок + /api/consistency (§10)"
```
