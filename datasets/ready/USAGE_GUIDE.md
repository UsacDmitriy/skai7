# SKAI Vibe Sprint 2026: инструкция по датасетам

Этот пакет подготовлен как offline-ready набор данных для кейсов хакатона. Внутри есть CSV-таблицы, MP4-ролики видеоаналитики и уже разложенные данные по задачам в `tasks/*/data`.

Для будущего продолжения выгрузок через SKAI MCP отдельно сохранена техническая шпаргалка: `datasets/ready/SKAI_MCP_USAGE.md`.

## Быстрый старт

1. Распакуйте основной архив:

```bash
unzip datasets/skai_vibesprint2026_ready_datasets.zip -d skai_dataset
```

2. Откройте главный каталог готовых данных:

```text
skai_dataset/datasets/ready/
```

3. Для видео откройте каталог медиа:

```text
skai_dataset/datasets/media/video_events/
```

4. Для конкретной задачи можно использовать уже подготовленный каталог:

```text
skai_dataset/tasks/<номер_задачи>/data/
```

Все CSV сохранены в UTF-8. Времена в API-выгрузках обычно в UTC (`*_utc`, ISO 8601). Денежные поля в рублях, топливо в литрах, дистанции в километрах, скорости в км/ч.

## Состав архивов

Основной архив:

```text
datasets/skai_vibesprint2026_ready_datasets.zip
```

Содержит все готовые CSV, MP4 видеоаналитики, README, `SKAI_MCP_USAGE.md` и данные, скопированные в папки задач.

Отдельный видео-архив:

```text
datasets/skai_vibesprint2026_video_events.zip
```

Содержит видео-событийный набор, MP4, данные для задач `03` и `05`, а также `SKAI_MCP_USAGE.md` для продолжения MCP-выгрузок.

## Главные папки

```text
datasets/ready/fuel_reconciliation/
datasets/ready/sensor_diagnostics/
datasets/ready/navigation_problem_tracks/
datasets/ready/normal_tracks_zis/
datasets/ready/video_events/
datasets/ready/reference/
datasets/media/video_events/
tasks/*/data/
```

`datasets/ready/manifest.csv` содержит быстрый счетчик строк по основным таблицам. На момент сборки:

- `fuel_card_transactions`: 30
- `fuel_events`: 27
- `fuel_reconciliation`: 30
- `bo_sensor_graph_points`: 959782
- `bo_track_points`: 81977
- `video_events_vehicles`: 21
- `video_events_selected_video_alarms`: 54
- `video_events_video_files`: 94
- `video_events_track_points`: 6635
- `video_events_media_files`: 94
- `video_events_work_rest_single_vehicle_alarms`: 6
- `video_events_work_rest_single_vehicle_video_files`: 6
- `video_events_work_rest_single_vehicle_track_points`: 628

## Рекомендуемая работа с CSV

В Python:

```python
from pathlib import Path
import pandas as pd

root = Path("datasets/ready")
fuel = pd.read_csv(root / "fuel_reconciliation/fuel_reconciliation.csv")
video = pd.read_csv(root / "video_events/video_files.csv")
tracks = pd.read_csv(root / "video_events/track_points.csv")
```

В Streamlit-шаблонах задач загрузчик уже ищет данные в `./data`, а если там пусто, берет `./sample_data`. Для реальной работы используйте `tasks/<task>/data`, потому что туда уже скопированы релевантные CSV.

## Связи и ключи

Основные ключи:

- `vehicle_id` - внутренний код машины в подготовленном датасете топлива и ZiS.
- `public_unit_id` - UUID машины в публичном SKAI API.
- `public_terminal_id` - UUID терминала в публичном SKAI API.
- `legacy_unit_id` - числовой id из legacy/ZiS отчетов.
- `unit_id` - UUID машины в BO/VA выгрузках.
- `terminal_id` / `TerminalId` - UUID терминала в VA/BO данных.
- `alarm_id` / `AlarmId` - UUID видеоаларма.
- `telemetry_id` / `TelemetryId` - id телеметрического события, по которому найдены видеофайлы.
- `video_file_id` - id MP4-файла для скачивания из media service.
- `dataset_vehicle_code` - короткий стабильный код машины в видео-наборе.

Типовые соединения:

- Топливная сверка: `fuel_reconciliation.vehicle_id` -> `fuel_vehicles.vehicle_id`.
- Топливные события: `fuel_events.vehicle_id` -> `fuel_vehicles.vehicle_id`.
- Транзакции карт: `fuel_card_transactions.vehicle_id` -> `fuel_vehicles.vehicle_id`.
- Диагностика датчиков: `sensor_graph_points.public_unit_id` -> `sensor_targets.public_unit_id`.
- Каталог датчиков: `sensor_graph_points.sensor_id` + `public_unit_id` -> `sensor_catalog.sensor_id` + `public_unit_id`.
- Проблемные треки: `track_points.public_unit_id` -> `navigation_problem_vehicles.public_unit_id`.
- Видео: `video_files.alarm_id` -> `selected_video_alarms.AlarmId`.
- Видео + треки: `video_files.alarm_id` -> `track_points.alarm_id`.
- Видео + машина: `video_files.dataset_vehicle_code` -> `vehicles.dataset_vehicle_code`.

## Датасет топлива

Папка:

```text
datasets/ready/fuel_reconciliation/
```

Назначение: кейсы сверки заправок по топливным картам, датчикам уровня топлива и ZiS-отчетам.

Файлы:

- `fuel_vehicles.csv` - список машин, карты, VIN, сопоставление с legacy/ZiS, агрегаты по объемам.
- `fuel_card_transactions.csv` - транзакции топливных карт: карта, время, объем, сумма, станция, тип топлива.
- `fuel_events.csv` - события датчика топлива: заправки/сливы, объем до/после, координаты.
- `fuel_reconciliation.csv` - готовая сверка транзакция-к-событию, статус, риск, причина.
- `fuel_summary.csv` - агрегаты расхода и топлива по машине.
- `station_summary.csv` - агрегаты по станциям/процессинговым центрам.

Главная таблица для приложения: `fuel_reconciliation.csv`.

Рекомендуемые сценарии:

- найти транзакции без подтверждения датчиком;
- найти заправки/сливы без транзакций карты;
- ранжировать риск по `risk_score`;
- построить карточку машины из `fuel_vehicles.csv` + `fuel_summary.csv`;
- показать карту событий по `lat`, `lon`.

## Датасет датчиков

Папка:

```text
datasets/ready/sensor_diagnostics/
```

Назначение: кейсы диагностики датчиков, поиска пропусков, аномалий и проблем с данными от объекта.

Файлы:

- `sensor_targets.csv` - машины из исходного списка, периоды, описания проблем, SKAI match.
- `sensor_catalog.csv` - каталог датчиков по терминалу: id, имя, группа, тип, output mode.
- `sensor_graph_points.csv` - точечные значения графиков датчиков.
- `sensor_graph_status.csv` - статус выгрузки графиков по дню и датчику.
- `online_snapshot.csv` - online-снимок машины: скорость, топливо, координаты, спутники, одометр.
- `engine_statistics.csv` - статистика работы двигателя.
- `fuel_level_summary.csv` - первый/последний уровень топлива за период.
- `mileage_and_speed.csv` - дневные пробеги, скорость, движение/стоянка.
- `daily_mileage.csv` - дневной пробег.

Главная таблица для анализа сигналов: `sensor_graph_points.csv`.

Рекомендуемые сценарии:

- выбрать машину из `sensor_targets.csv`;
- найти ее датчики в `sensor_catalog.csv`;
- построить временной ряд из `sensor_graph_points.csv`;
- проверить покрытие по `sensor_graph_status.csv`;
- сравнить график топлива с `fuel_level_summary.csv`;
- искать резкие скачки, плато, пропуски, постоянные нули, выбросы.

Важные поля `sensor_graph_points.csv`:

- `public_unit_id`
- `vehicle_id`
- `date`
- `sensor_id`
- `sensor_name`
- `sensor_group`
- `sensor_type`
- `timestamp_utc`
- `value`

## Датасет проблемных треков

Папка:

```text
datasets/ready/navigation_problem_tracks/
```

Назначение: кейсы поиска плохих треков, разрывов навигации, завышенных скоростей и несоответствий GPS/одометр.

Файлы:

- `navigation_problem_vehicles.csv` - машины, периоды, описание проблемы, SKAI match.
- `track_points.csv` - точечные координаты, скорость, курс, EW-флаг.
- `track_periods.csv` - периоды движения/стоянки/разрывов.
- `track_fetch_status.csv` - статус выгрузки трека по машине и дню.
- `problem_track_daily_stats.csv` - дневные агрегаты по пробегам/скоростям.
- `problem_track_period_stats.csv` - агрегаты по периодам.
- `daily_mileage.csv` - дневной пробег.

Главная таблица для карты: `track_points.csv`.

Рекомендуемые сценарии:

- строить трек по `latitude`, `longitude`;
- искать точки с большой `speed_kmh`;
- находить разрывы по времени между соседними `timestamp`;
- сравнивать `gps_total_distance_km` и `distance_odometer_km`;
- использовать `track_fetch_status.csv`, чтобы не считать пустые дни ошибкой приложения.

Известное ограничение: для `О834МР193` за `2026-05-09` и `2026-05-10` API вернул пусто/ошибки. Это отражено в статусных таблицах.

## Нормальные ZiS-треки и контекст

Папка:

```text
datasets/ready/normal_tracks_zis/
```

Назначение: дать командам не только проблемные, но и нормальные/контекстные данные для сравнения.

Файлы:

- `normal_vehicle_period_metrics.csv` - нормальные машины из ZiS с агрегатами по топливу и пробегу.
- `normal_vehicle_fuel_events.csv` - события топлива для этих машин.

Рекомендуемые сценарии:

- использовать как baseline для кейсов с аномалиями;
- сравнивать нормальные и проблемные машины;
- добавлять нормальный контекст в поддержку/диагностику.

## Видеоаналитика

Папки:

```text
datasets/ready/video_events/
datasets/media/video_events/
```

Назначение: кейсы видеоаналитики, контроля водителя, единого окна "видео + телеметрия", обучения мер реагирования.

Состав:

- 21 машина;
- 54 видеоаларма, включая 12 Smoking и 15 Drowsiness;
- 94 MP4-ролика;
- 6635 точек треков вокруг видеоалармов;
- 1003.495 секунд видео суммарно;
- все ролики `video/mp4`, codec `h264`.

Файлы:

- `vehicles.csv` - сводка по видео-машинам.
- `selected_video_alarms.csv` - выбранные видеоалармы.
- `video_files.csv` - связь аларма с MP4: канал, id файла, путь, размер, длительность, codec.
- `track_summary.csv` - сводка трек-окна вокруг каждого аларма.
- `track_periods.csv` - периоды движения/стоянки вокруг аларма.
- `track_points.csv` - точки трека вокруг аларма.
- `max_speed_points.csv` - точки максимальной скорости.
- `work_rest_single_vehicle/` - компактный поднабор на одном объекте для кейса режима труда и отдыха: `У126ТК124` (`U126TK124`), 6 событий Drowsiness и 6 MP4 за `2026-05-18`.

MP4 лежат в:

```text
datasets/media/video_events/
```

Для переносимого пути используйте поле:

```text
video_files.media_relative_path
```

Поля `local_path` и `media_relative_path` нормализованы как относительные пути от корня архива/проекта. Для новых приложений лучше использовать `media_relative_path`; `local_path` оставлен для совместимости с уже выданной схемой.

Пример загрузки видео:

```python
from pathlib import Path
import pandas as pd

root = Path("skai_dataset")
video_files = pd.read_csv(root / "datasets/ready/video_events/video_files.csv")
first = video_files.iloc[0]
mp4_path = root / first["media_relative_path"]
print(mp4_path)
```

Рекомендуемые сценарии:

- показать аларм, ролики разных каналов и трек рядом;
- классифицировать события по `event_type`;
- сравнить скорость в аларме и скорость в `track_points`;
- искать похожие события у разных машин;
- строить единую карточку события по `selected_video_alarms.csv` + `video_files.csv` + `track_summary.csv`.

## Reference-таблицы

Папка:

```text
datasets/ready/reference/
```

Файлы:

- `vehicle_matches.csv` - итоговое сопоставление исходных машин с публичными SKAI ids.
- `vehicle_match_candidates.csv` - кандидаты матчинга и score.
- `zis_legacy_matches.csv` - сопоставление с legacy/ZiS ids.

Используйте эти таблицы, если нужно объяснить, почему в разных слоях данных разные id для похожей машины.

## Данные в папках задач

Данные уже разложены в соответствующие задачи:

- `tasks/01_fuel_cards_reconciliation/data` - топливная сверка.
- `tasks/02_proactive_support_agents/data` - проблемные треки и статусы.
- `tasks/03_driver_substitution_video/data` - видеоалармы, MP4 metadata, треки вокруг видео.
- `tasks/04_driver_gamification/data` - производные таблицы лидерборда, нарушений и eco/safety метрик из видеоалармов.
- `tasks/05_video_telematics_single_window/data` - видеоалармы, MP4 metadata, треки вокруг видео.
- `tasks/06_fuel_station_optimizer/data` - топливо, транзакции, станции.
- `tasks/07_driver_measures_training/data` - производные нарушения, водители-прокси, каталог мер и рекомендованные меры.
- `tasks/08_vehicle_predictive_diagnostics/data` - датчики, графики, online snapshot, пробег/скорость/топливо/зажигание.
- `tasks/09_vehicle_inspection_release/data` - нормальные ZiS-машины как эксплуатационный референс.

В задачах 04 и 07 `driver_id` является демо-прокси на базе машины: реальная идентификация водителя в подготовленном экспорте не выгружалась.

## Быстрая проверка целостности

После распаковки можно проверить, что CSV и MP4 на месте:

```python
from pathlib import Path
import pandas as pd

root = Path("skai_dataset")
manifest = pd.read_csv(root / "datasets/ready/manifest.csv")
print(manifest)

video = pd.read_csv(root / "datasets/ready/video_events/video_files.csv")
assert (video["download_status"] == "downloaded").all()
assert len(list((root / "datasets/media/video_events").glob("*.mp4"))) == len(video)
for rel in video["media_relative_path"]:
    assert (root / rel).exists(), rel
```

Для видео можно дополнительно проверить codec через `ffprobe`, если он установлен:

```bash
ffprobe -v error -select_streams v:0 -show_entries stream=codec_name,width,height -of default=nw=1 datasets/media/video_events/*.mp4
```

## Известные ограничения

- Данные не являются полным продовым срезом SKAI. Это curated-набор для хакатона.
- В разных источниках одна и та же машина может иметь разные id: используйте reference-таблицы.
- Временные зоны смешаны по источникам; поля с суффиксом `_utc` уже нормализованы в UTC.
- Для части исходных машин API мог вернуть пустые дни; это не удалено, а отражено в `*_status.csv`.
- Видеофайлы скачаны из VA media по `VaAlarmVideo.Id`; если переносить только CSV без `datasets/media/video_events`, видео не откроется.
- Координаты и адреса могут быть пустыми в отдельных строках, если исходный API их не вернул.

## Как выбирать данные под кейс

Топливная сверка:

```text
fuel_reconciliation/fuel_reconciliation.csv
fuel_reconciliation/fuel_card_transactions.csv
fuel_reconciliation/fuel_events.csv
fuel_reconciliation/fuel_vehicles.csv
```

Оптимизация АЗС:

```text
fuel_reconciliation/fuel_card_transactions.csv
fuel_reconciliation/station_summary.csv
fuel_reconciliation/fuel_vehicles.csv
```

Диагностика датчиков:

```text
sensor_diagnostics/sensor_targets.csv
sensor_diagnostics/sensor_catalog.csv
sensor_diagnostics/sensor_graph_points.csv
sensor_diagnostics/sensor_graph_status.csv
```

Проблемные треки и поддержка:

```text
navigation_problem_tracks/navigation_problem_vehicles.csv
navigation_problem_tracks/track_points.csv
navigation_problem_tracks/track_fetch_status.csv
navigation_problem_tracks/problem_track_daily_stats.csv
```

Видеоаналитика:

```text
video_events/selected_video_alarms.csv
video_events/video_files.csv
video_events/track_points.csv
datasets/media/video_events/*.mp4
```

Обучение мер реагирования:

```text
video_events/selected_video_alarms.csv
video_events/video_files.csv
sensor_diagnostics/online_snapshot.csv
navigation_problem_tracks/problem_track_daily_stats.csv
```

## Происхождение данных

Источники:

- `source_data.xlsx` - исходные списки машин и транзакции.
- `Топливо/` - локальные ZiS-отчеты по заправкам и сливам.
- SKAI public/statistics API - агрегаты, online snapshot, mileage/speed.
- SKAI BO API - sensor graph, tracks, VA alarms.
- SKAI media service - MP4 по видеоалармам.

Сырые ответы API сохранялись в `datasets/raw/`, но основной архив предназначен для работы с подготовленным слоем `datasets/ready/` и `datasets/media/`.
