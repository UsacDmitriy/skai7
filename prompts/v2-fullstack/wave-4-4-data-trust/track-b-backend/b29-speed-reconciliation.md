# b29 · Кросс-сверка скоростей событие↔GPS-трек (фича #21, владелец §10.3-часть 2)

> Трек **Backend/Data**. Против `00-CONTRACT.md` §10.2/§10.3/§10.5. **Владеет:** `api/sql/35_v_speed_check.sql`,
> `api/services/speed_check_service.py`, `api/domain/speed.py`, роутер `api/routers/speed_check.py`
> (автодискавери `api/main.py:_discover_routers` — НЕ редактируй общий `api/routers/__init__.py`).
> **Модель:** 🔵 Sonnet — детерминированный SQL против контракта; гейт = Check + tu-consistency.
> **Волна 4.4**, окно 1 (backend), **после b28** (последовательно; файлы не пересекаются — §10.6).
> После создания `v_speed_check` — замени CTE-заглушку `speed_disagreement` в `34_v_consistency.sql` (см. b28).

## Контекст (зачем)

Фомин (PepsiCo): «видеоаналитика показывает одну скорость, телеметрия CAN — другую; истина — CAN».
Сверка скоростей из независимых источников на каждом инциденте — ядро доверия к данным единого окна.

## Цель

`GET /api/incidents/{id}/speed-check` → `SpeedCheck` (§10.2): сравнение скорости из события аларма
и ближайшей точки GPS-трека (±10 с) с классификацией расхождения `ok/minor/major/no_data` —
видимый слой доверия к скорости на каждом инциденте.

## ASSUMPTION (зафиксировано в §10.2 — не менять молча)

CAN-скорости в датасете **нет**. Источник истины — **GPS-трек** (`video_events__track_points.speed_kmh`),
в ответе всегда `truth_source: 'gps_track'`. Требование «истина = CAN» аппроксимируется GPS до появления
CAN-датасета (Волна 5, `WAVE-5-BACKLOG.md` W5-5). В UI писать «GPS-трек», НЕ «CAN».

## Состав

- `api/sql/35_v_speed_check.sql` — view `v_speed_check` (строка на аларм). Скелет (достроить):

  ```sql
  CREATE OR REPLACE VIEW v_speed_check AS
  WITH nearest AS (
    SELECT alarm_id, speed_kmh, timestamp_utc,
           row_number() OVER (
             PARTITION BY alarm_id
             ORDER BY abs(epoch(timestamp_utc) - epoch(event_begin_utc))
           ) AS rn,
           abs(epoch(timestamp_utc) - epoch(event_begin_utc)) AS dist_s
    FROM video_events__track_points
  )
  SELECT CAST(a."AlarmId" AS VARCHAR)            AS id,
         CAST(NULLIF(CAST(a."Speed" AS VARCHAR), '') AS DOUBLE) AS event_speed_kmh,
         CASE WHEN n.dist_s <= 10 THEN n.speed_kmh END          AS track_speed_kmh,
         m.max_speed_kmh                                        AS max_track_speed_kmh
  FROM video_events__selected_video_alarms a
  LEFT JOIN nearest n ON n.alarm_id = CAST(a."AlarmId" AS VARCHAR) AND n.rn = 1
  LEFT JOIN (SELECT alarm_id, max(speed_kmh) AS max_speed_kmh
             FROM video_events__max_speed_points GROUP BY alarm_id) m
    ON m.alarm_id = CAST(a."AlarmId" AS VARCHAR);
  ```

  Окно ближайшей точки — **±10 с** от начала события (`event_begin_utc` уже есть в `track_points`).
  ASOF JOIN **не использовать** (оконная функция проще и детерминированнее).
  ⚠️ Типы `alarm_id` в CSV могут отличаться (число/строка) — приводить обе стороны JOIN к `VARCHAR`.

- `speed_check_service.speed_check(id) -> SpeedCheck` (§10.2):
  - `delta_kmh = abs(event_speed − track_speed)` (оба не NULL), иначе `null`;
  - `agreement`: `no_data` если любой из источников NULL; иначе `ok` ≤ 5 · `minor` ≤ 15 · `major` > 15;
  - неизвестный `id` → 404; всё детерминированно, без сети.
- `api/domain/speed.py` — Pydantic `SpeedCheck` **дословно по §10.2**.
- Роутер `GET /api/incidents/{id}/speed-check` (файл `api/routers/speed_check.py`, модульный `router`).
- Заменить заглушку `speed_disagreement` в `34_v_consistency.sql`:
  `SELECT 'speed_disagreement', COUNT(*) FILTER (WHERE agreement-условие major), COUNT(*) FROM v_speed_check`
  (условие major вычислять в SQL зеркально сервисным порогам §10.2).

Примеры ответов (формат — ровно такой):

```json
{ "id": "12345", "event_speed_kmh": 32.0, "track_speed_kmh": 28.4,
  "max_track_speed_kmh": 41.0, "delta_kmh": 3.6, "agreement": "ok", "truth_source": "gps_track" }
```

```json
{ "id": "67890", "event_speed_kmh": null, "track_speed_kmh": null,
  "max_track_speed_kmh": null, "delta_kmh": null, "agreement": "no_data", "truth_source": "gps_track" }
```

## Check

- `make db` → `v_speed_check` создан; строк = числу алармов (LEFT JOIN ничего не теряет).
- `curl -s localhost:8000/api/incidents/<известный id>/speed-check | jq -e '.truth_source=="gps_track"'` → 200.
- `test "$(curl -s -o /dev/null -w '%{http_code}' localhost:8000/api/incidents/__nope__/speed-check)" = 404`.
- Существует аларм с `agreement="no_data"` → ответ 200, не 5xx (негатив §10.5).
- Пороги: подобрать алармы с delta в каждой зоне (ok/minor/major) или проверить классификатор юнитом (tu-consistency).
- `curl -s localhost:8000/openapi.json | jq -e '.paths."/api/incidents/{id}/speed-check"'` — автодискавери.
- Детерминизм: два вызова → идентичный ответ. `curl -s localhost:8000/api/consistency | jq -e '.checks|length==7'`
  — заглушка `speed_disagreement` заменена, отчёт b28 не сломан.

## Коммит (обязательно)

Заверши промпт коммитом в свою ветку — **merge на барьере берёт только коммиты**:

```bash
# стейджи только свои файлы (НЕ git add -A); 34_*.sql — согласованная правка заглушки (см. Состав)
git add api/sql/35_v_speed_check.sql api/sql/34_v_consistency.sql api/services/speed_check_service.py api/routers/speed_check.py api/domain/speed.py
git commit -m "b29: кросс-сверка скоростей событие↔GPS — /speed-check + v_speed_check (§10)"
```
