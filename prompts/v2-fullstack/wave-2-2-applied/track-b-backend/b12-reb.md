# b12 · РЭБ / GPS-разрывы — v_reb + сервис + роутер

> Трек **Backend/Data**. Против `00-CONTRACT.md` §7.2/§7.4/§7.5 (идея #8). **Владеет:** `api/sql/24_v_reb.sql`, `api/services/reb_service.py`, `api/routers/reb.py`.
> **Модель:** 🔵 Sonnet — детерминированная логика/вёрстка против контракта; гейт = секция Check.
> Кодит против контракта. **Зависит от:** b1 (таблицы `navigation__track_periods`, `navigation__track_points`, `video_events__video_files`). Параллелится с b10/b11/b13 (разные файлы). Роутер включается в `api/main.py` (x2/b6). Заменяет стаб `navigation` → `/api/reb` (§7.4).

## Цель

Восстановление трека при подавлении GPS (идея #8, РЭБ): найти разрывы навигации
(`period_type=3` — потеря сигнала) и сшить картину соседними видимыми периодами и видеокадрами,
чтобы показать, что ТС двигалось, пока GPS «молчал».

## SQL-view `api/sql/24_v_reb.sql` → `v_reb`

Начать с `DROP VIEW IF EXISTS "v_reb"`. Из `"navigation__track_periods"`:

- Разрывы: строки с `"period_type" = 3` → `start`, `end`, `duration_sec` (длительность периода).
- Соседние видимые периоды: периоды до/после разрыва с валидным GPS (для сшивки трека).
- Ключ ТС: `vehicle_plate`/`unit_id` (как в navigation-таблицах).
- View отдаёт «сырое» по периодам; сборку `gps_track`/`video_frames` под схему делает сервис.

## Сервис `api/services/reb_service.py`

- `get_reb(db, id) -> RebRecovery | None` (схема §7.5):
  - `gps_track: {lat,lon,ts}[]` — точки из `"navigation__track_points"` видимых периодов вокруг разрыва.
  - `gap_periods: {start,end,duration_sec}[]` — разрывы из `v_reb` для данного ТС/`id`.
  - `video_frames: {ts, channel, url}[]` — кадры из `"video_events__video_files"`, попадающие во временные
    окна разрывов (доказательство движения при отсутствии GPS).
  - `vehicle_plate` — госномер.
  - `None`, если по `id` нет данных навигации (роутер → 404).

## Роутер `api/routers/reb.py`

- `GET /api/reb/{id}` → `RebRecovery` (§7.4); 404 если нет данных.
- Паттерн роутеров b6: `APIRouter(prefix="/api", tags=["reb"])`, DI соединения DuckDB.

## Edge cases / поведение

- `gap_periods` собираются только из `"period_type" = 3` (потеря GPS); периоды с валидным GPS в разрывы не попадают.
- Непрерывный трек (нет ни одного `period_type=3` у ТС) → `gap_periods = []`; сервис всё равно может вернуть `RebRecovery` с пустым списком разрывов (трек целый).
- По `id` нет данных навигации вовсе → `get_reb` возвращает `None` (роутер → 404), а не пустой `RebRecovery`.
- `video_frames` — только кадры, попадающие во временные окна разрывов; вне окон не включаются.
- Граница разрыва: `start`/`end`/`duration_sec` берутся из периода; `duration_sec ≥ 0` (не отрицательная).

## Check

- После `make db`: `SELECT * FROM "v_reb" LIMIT 5` без ошибок; в выборке только периоды с `"period_type"=3` и их соседи.
- `GET /api/reb/{id}` для существующего ТС возвращает `RebRecovery` с непустыми `gap_periods`;
  `gps_track` и `video_frames` — массивы (могут быть пустыми, но валидны).
- ТС с непрерывным треком → `gap_periods = []` (валидный ответ, не 404).
- `GET /api/reb/{неизвестный}` → 404 (`get_reb` вернул `None`).
- Повторный `make db` пересоздаёт view без дублей.
