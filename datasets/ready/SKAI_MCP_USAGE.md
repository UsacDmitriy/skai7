# SKAI MCP usage notes for future agents

Этот файл - короткая инструкция для агентов, которые будут продолжать сборку датасетов SKAI Vibe Sprint 2026. Он фиксирует реальные MCP-инструменты и особенности вызовов, найденные при подготовке текущего набора.

## С чего начинать

Если `mcp__skai__` tools не видны в активном контексте, сначала вызови discovery:

```text
tool_search query: skai MCP list alarms download video call operation tracks graph sensors units VaAlarmVideo
```

После этого в сессии обычно появляются typed-tools из namespace `mcp__skai__`.

Основной принцип: для частых задач используй typed-tools, для редких BO/OData endpoints - `skai_list_operations` + `skai_call_operation`.

## Основные typed-tools

### Датчики и графики

Получить список датчиков терминала:

```text
mcp__skai__.skai_bo_composer_get_sensors({
  "terminal_id": "<public_terminal_id>"
})
```

Рабочий BO endpoint: `GET https://bo.skai.online/api/sensors/{terminalId}`.

Получить точки графика датчиков:

```text
mcp__skai__.skai_bo_statistics_unit_graph_v2({
  "unit_id": "<public_unit_id>",
  "sensor_ids": ["<sensor_id_1>", "<sensor_id_2>"],
  "date_from": "2026-05-04T00:00:00+03:00",
  "date_to": "2026-05-05T00:00:00+03:00"
})
```

Рабочий BO endpoint: `POST https://bo.skai.online/statistics/units/graph/V2`.

Практика для больших периодов: выгружать по дням, сохранять статус каждой дневной выгрузки и не считать пустой день ошибкой, если API вернул корректный пустой ответ.

### Треки и телеметрия

Получить трек по объекту:

```text
mcp__skai__.skai_bo_composer_get_tracks_by_unit({
  "unit_id": "<public_unit_id>",
  "date_from": "2026-05-09T00:00:00+00:00",
  "date_to": "2026-05-10T00:00:00+00:00",
  "include_ew_points": true,
  "tolerance": 0
})
```

Рабочий BO endpoint: `GET https://bo.skai.online/api/tracks/by-unit`.

Важная особенность: не использовать `/composer/api/tracks/by-unit` и `/online-data/api/tracks/by-unit`; для этой выгрузки работал именно `/api/tracks/by-unit` на `bo.skai.online`.

Для проблемных треков лучше выгружать отдельно по дням. Для видео-событий использовалось окно около 15 минут до `Begin` и 15 минут после `End` каждого аларма.

### Видеоалармы

Список VA alarm events:

```text
mcp__skai__.skai_bo_va_list_alarms({
  "limited": false,
  "query": {
    "$filter": "Begin ge 2026-05-12T00:00:00Z and Begin lt 2026-05-19T00:00:00Z and VideoCount gt 0 and (Type eq 'Drowsiness' or Type eq 'Smoking')",
    "$orderby": "Begin desc",
    "$top": 100
  }
})
```

Рабочий endpoint: `GET https://bo.skai.online/va/odata/VaAlarms`.

Особенности OData:

- Имена полей PascalCase: `Begin`, `End`, `Type`, `VideoCount`, `TelemetryId`.
- Даты для VA OData удобно передавать в UTC с `Z`.
- Для выборки курения/засыпания использовались типы `Smoking` и `Drowsiness`.

Получить видеофайлы аларма нужно по `TelemetryId`, а не по `AlarmId`:

```text
mcp__skai__.skai_bo_va_list_alarm_videos({
  "telemetry_id": "<TelemetryId from VaAlarms row>"
})
```

Рабочий endpoint: `GET https://bo.skai.online/va/odata/VaAlarmVideo`.

Важная особенность: `TelemetryId` в `VaAlarmVideo` хранится как `Edm.String`, поэтому UUID-похожее значение в OData filter должно быть в кавычках. Typed-tool делает это сам.

### Скачивание видео

Для `VaAlarmVideo.Id` используй специальный downloader:

```text
mcp__skai__.skai_download_va_alarm_video({
  "video_id": "<VaAlarmVideo.Id>",
  "save_to": "datasets/media/video_events/<relative-name>.mp4"
})
```

Рабочий endpoint под капотом: `GET https://vasign.skai.online/media-files/data/{VaAlarmVideo.Id}`.

Что было проверено и не подошло:

- `HEAD` на production media service возвращал `405`.
- `/media-files/data/va-alarms/{id}` для `VaAlarmVideo.Id` возвращал `404`.
- `mcp__skai__.skai_download_media_file({kind: "alarm"})` не подходит для `VaAlarmVideo.Id`.
- `mcp__skai__.skai_download_media_file({kind: "regular"})` подходит для обычных media file ids, но для VA alarm video ids лучше использовать `skai_download_va_alarm_video`.

## Generic OpenAPI calls

Для endpoints, которых нет typed-tool, используй:

```text
mcp__skai__.skai_list_operations({
  "api": "bo_composer",
  "search": "tracks",
  "limit": 20
})
```

Затем:

```text
mcp__skai__.skai_call_operation({
  "operation": "bo_composer.Tracks_get_api_tracks_by_unit",
  "query": {
    "unitId": "<public_unit_id>",
    "dateFrom": "2026-05-18T21:45:39+00:00",
    "dateTo": "2026-05-18T22:15:46+00:00",
    "includeEwPoints": true,
    "tolerance": 0
  }
})
```

Операции, реально использованные при сборке:

- `bo_statistics.CalculateGraphByUnitIdV2` - точки графика датчиков.
- `bo_composer.Tracks_get_api_tracks_by_unit` - треки/телеметрия объекта.
- `bo_composer.GetSensors` - каталог датчиков терминала.
- `bo_va.odata/VaAlarms` - события видеоаналитики.
- `bo_va.odata/VaAlarmVideo` - видеофайлы по `TelemetryId`.
- `media.MediaFiles_get_media_files_data_va_alarms_by_id` - был проверен, но для `VaAlarmVideo.Id` возвращал `404`; не использовать для этих роликов.

## Где сохранять результаты

Текущая структура датасета:

```text
datasets/ready/
datasets/raw/
datasets/media/video_events/
tasks/*/data/
```

Raw-ответы SKAI:

```text
datasets/raw/video_events/tracks/<alarm_id>.json
datasets/raw/video_events/va_alarm_videos/<alarm_id>.json
datasets/raw/va_alarms_2026-05-12_2026-05-19_drowsiness_smoking_video_gt0_top100.json
```

MP4:

```text
datasets/media/video_events/<dataset_vehicle_code>__<yyyymmddHHMM>__<event_type>__alarm_<short_alarm_id>__ch<channel>__<video_id>.mp4
```

В `video_files.csv` пути должны оставаться относительными от корня архива/проекта:

```text
datasets/media/video_events/...
```

Не записывай абсолютные пути вида `/Users/...` в CSV, если файл должен попадать в архив.

## Проверки после выгрузки

Минимальные проверки перед архивированием:

```bash
python3 - <<'PY'
import csv
from pathlib import Path

rows = list(csv.DictReader(open("datasets/ready/video_events/video_files.csv", newline="", encoding="utf-8")))
print("video_files", len(rows))
print("abs local_path", sum((r.get("local_path") or "").startswith("/") for r in rows))
print("abs media_relative_path", sum((r.get("media_relative_path") or "").startswith("/") for r in rows))
print("not downloaded", sum(r.get("download_status") != "downloaded" for r in rows))
print("missing files", sum(not Path(r["media_relative_path"]).exists() for r in rows))
PY
```

Проверка архива:

```bash
python3 - <<'PY'
import csv, zipfile
from pathlib import Path

media_paths = {r["media_relative_path"] for r in csv.DictReader(open("datasets/ready/video_events/video_files.csv", newline="", encoding="utf-8"))}
for zpath in [Path("datasets/skai_vibesprint2026_ready_datasets.zip"), Path("datasets/skai_vibesprint2026_video_events.zip")]:
    with zipfile.ZipFile(zpath) as z:
        names = set(z.namelist())
        print(zpath)
        print("  testzip:", z.testzip())
        print("  mp4:", sum(n.endswith(".mp4") for n in names))
        print("  missing media refs:", len([p for p in media_paths if p not in names]))
PY
```

## Что важно помнить

- Исторический отчет с точным названием `Сообщения от объекта` в найденном MCP/OpenAPI catalog не был доступен. Для датасета использовались ближайшие message-level источники: BO sensor graph V2 и BO tracks by unit.
- Для видео сначала выбирай алармы, затем получай `VaAlarmVideo` по `TelemetryId`, затем скачивай MP4 по `VaAlarmVideo.Id`.
- Для режима труда и отдыха есть готовый one-object поднабор: `datasets/ready/video_events/work_rest_single_vehicle/`.
- Для проблемных треков и датчиков масштабируй выгрузку по дням, чтобы легче повторять неудачные периоды и сохранять понятный статус.
- После любых изменений в видео-наборе обновляй `datasets/ready/manifest.csv`, `datasets/ready/USAGE_GUIDE.md`, `datasets/ready/video_events/README.md` и оба архива.
