# b11 · Саботаж камер — v_sabotage + сервис + роутер

> Трек **Backend/Data**. Против `00-CONTRACT.md` §7.2/§7.4/§7.5 (идея #9). **Владеет:** `api/sql/23_v_sabotage.sql`, `api/services/sabotage_service.py`, `api/routers/sabotage.py`.
> **Исполнение:** bounded ClinePass package; role `worker`; route category `code`; exact route/model only from `tools/clinepass-mcp/models.env` — детерминированная логика/вёрстка против контракта; гейт = секция Check.
> Кодит против контракта. **Зависит от:** b1 (таблицы `video_events__selected_video_alarms`, `video_events__track_points`, `video_events__video_files`), b7 (`driver_reference` для `driver_name`). Параллелится с b10/b12/b13 (разные файлы). Роутер включается в `api/main.py` (x2/b6).

## Цель

Детектор саботажа камеры (идея #9): корреляция признака «камера ослеплена/закрыта» с фактом
движения ТС. Если DMS-канал тёмный, а ТС едет (`speed_kmh>0`) — водитель, вероятно, заклеил камеру.

## SQL-view `api/sql/23_v_sabotage.sql` → `v_sabotage`

Начать с `DROP VIEW IF EXISTS "v_sabotage"` (идемпотентность b1). Корреляция:

- Признак саботажа: алярм типа `CAMERA_TAMPER` (по `"v_incidents".alarm_code`/`Type`) **или**
  «тёмный DMS-канал» (нет видимого DMS-кадра / `video_files` с `channel=5` отсутствует/недоступен).
- Условие движения: `speed_kmh > 0` (из `"video_events__track_points"` по алярму, либо `Speed` алярма).
- Колонки под схему `SabotageEvent` (§7.5): `id` (`AlarmId`), `vehicle_plate`, `ts`, `dms_dark` (bool),
  `speed_kmh`, `video_url` (`media_relative_path` доступного канала, nullable).
  `driver_name` досчитывает сервис через `driver_reference` (не материализуем в view).

## Сервис `api/services/sabotage_service.py`

- `list_sabotage(db) -> list[SabotageEvent]`:
  `SELECT * FROM "v_sabotage"` → для каждой строки обогатить `driver_name` через `driver_reference`
  (b7) по `vehicle_plate`; собрать Pydantic `SabotageEvent` (схема §7.5).

## Роутер `api/routers/sabotage.py`

- `GET /api/sabotage` → `list[SabotageEvent]` (§7.4). Без параметров.
- Стандартный паттерн роутеров b6: `APIRouter(prefix="/api", tags=["sabotage"])`, DI соединения DuckDB.

## Edge cases / поведение

- Событие саботажа = (тёмный DMS / `CAMERA_TAMPER`) **И** `speed_kmh > 0` — оба условия обязательны.
- `speed_kmh = 0` (ТС стоит) при тёмном DMS → **НЕ** событие (легитимная парковка/стоянка).
- DMS-канал `ok` (есть видимый кадр `channel=5`) при движении → **НЕ** событие.
- Нет ни одной строки-кандидата → `list_sabotage` возвращает пустой список `[]` (не ошибка, не 404).
- `video_url` nullable: если доступного канала нет → `null` (поле не обязано присутствовать).

## Check

- После `make db`: `SELECT * FROM "v_sabotage" LIMIT 5` выполняется без ошибок.
- В `v_sabotage` попадают только строки с признаком саботажа **и** `speed_kmh>0`; строки со `speed_kmh=0` и со «здоровым» DMS отсутствуют.
- `GET /api/sabotage` возвращает JSON-массив `SabotageEvent`; поля `dms_dark` (bool), `speed_kmh` (float), `driver_name` заполнены.
- Пустой `v_sabotage` → `GET /api/sabotage` отдаёт `[]` (HTTP 200), а не ошибку.
- `driver_name` берётся из `driver_reference`, при отсутствии — синтетика (через enrichment, как §7.1).
- Повторный `make db` пересоздаёт view без дублей.

## Коммит (обязательно)

Заверши промпт коммитом в свою ветку — **merge на барьере берёт только коммиты**; незакоммиченная
работа в worktree на барьер не попадёт:

```bash
git add -A && git commit -m "b11: <что сделано>"
```
