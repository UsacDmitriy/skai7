# b1 · DuckDB ETL — build_duckdb.py

> Трек **Backend/Data**. Против `00-CONTRACT.md` §1. **Владеет:** `api/etl/build_duckdb.py`.
> **Исполнение:** bounded ClinePass package; role `worker`; route category `code`; exact route/model only from `tools/clinepass-mcp/models.env` — механическая транскрипция против точной спеки; гейт ловит ошибку.
> ETL-сборка БД из CSV (логика самодостаточна: см. контракт §1; ранний SQLite-прототип портирован на DuckDB).

## Цель

Идемпотентный скрипт, собирающий `data/skai.duckdb` из всех CSV в `datasets/ready/` + справочник
`alarm_type_catalog`, затем применяющий SQL-файлы `api/sql/*.sql` (там view от b3).

## Требования

1. Рекурсивный обход `datasets/ready/**/*.csv`. Для каждого CSV:
   - префикс по таблице из §1.1 (по верхней папке; вложенная `work_rest_single_vehicle` → `video_events__wr`);
   - имя таблицы `"{prefix}__{csv_lowercase_без_.csv}"`;
   - загрузка через DuckDB: `CREATE OR REPLACE TABLE "<name>" AS SELECT * FROM read_csv_auto('<path>', header=true, all_varchar=false)`.
   - Колонки — дословно из заголовка CSV (регистр сохраняется).
2. Справочник: прочитать `data/analysis/alarm_types.json` поле `alarm_types` → `CREATE OR REPLACE TABLE "alarm_type_catalog"` с колонками `raw, code, label_ru, source, severity, requires_video, auto_request_video` (через DuckDB `read_json_auto` или из Python-списка → `executemany`/`from_df`).
3. После таблиц: выполнить **все** `api/sql/*.sql` в лексикографическом порядке (`conn.execute(sql_text)`); если папки/файлов нет — пропустить без ошибки (view добавит b3).
4. Идемпотентность: повторный запуск пересоздаёт всё (`CREATE OR REPLACE`, в SQL — `DROP VIEW IF EXISTS`).
5. Сигнатура и точки входа:
   ```python
   def build(db_path: Path = Path("data/skai.duckdb"),
             ready_dir: Path = Path("datasets/ready"),
             json_path: Path = Path("data/analysis/alarm_types.json"),
             sql_dir: Path = Path("api/sql")) -> None: ...
   ```
   `python -m api.etl.build_duckdb` и `python api/etl/build_duckdb.py`.
6. Вывод-сводка: число таблиц, строк в ключевых (`video_events__selected_video_alarms`=54, `alarm_type_catalog`=14), наличие view `v_incidents`.

## Зависимости

`duckdb` в `api/requirements.txt` (его заводит b4; здесь — только импорт). Не читать содержимое `datasets/` целиком в Python — грузить через DuckDB SQL.

## Check

- `python -m api.etl.build_duckdb` создаёт `data/skai.duckdb`.
- `SELECT count(*) FROM "video_events__selected_video_alarms"` = 54; `alarm_type_catalog` = 14.
- Коллизия имён отсутствует: существуют и `video_events__track_points`, и `navigation__track_points`.
- Повторный запуск не плодит дублей.
