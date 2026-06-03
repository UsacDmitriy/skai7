# Анализ датасетов SKAI — итоги

> Дата: 2026-06-03. Анализ выполнен по реальному содержимому [datasets/](datasets/) и сопоставлен
> с фронтендом ([backend/](backend/), Streamlit) и промптами разработки ([prompts/](prompts/)).

## ⚠️ Расхождение с исходным промптом

Промпт-задание предполагало файлы, которых в проекте **нет**: интервью `.docx`
(Фомин/Маслов/Оздоев), `texts.json` (CJM из Figma), `frames.json`, а также REST-эндпоинты.
Поэтому шаги «извлечь сущности из интервью» и «спроектировать REST API» неприменимы.

Фактически проект — это **Streamlit-приложение** (не REST). «Бэкенд» здесь = слой загрузки
данных [backend/data_loader.py](backend/data_loader.py), который читает CSV из [data/](data/) в
`dict[str, pd.DataFrame]`. Поэтому ниже — анализ реальных данных и того, как их организовать
под существующую UI-схему инцидента.

## Источники данных

| Набор | Где | Объём |
|---|---|---|
| Видео-алярмы | [datasets/ready/video_events/](datasets/ready/video_events/) | 54 алярма, 21 ТС |
| Видеофайлы (mp4) | [datasets/media/video_events/](datasets/media/video_events/) | 94 файла, каналы ch1/2/3/5 |
| Треки событий | `video_events/track_*.csv` | 112 периодов, 6 635 точек |
| Топливо/сверка | [datasets/ready/fuel_reconciliation/](datasets/ready/fuel_reconciliation/) | карты, заправки/сливы |
| Датчики | [datasets/ready/sensor_diagnostics/](datasets/ready/sensor_diagnostics/) | ~960k точек графиков |
| Проблемные треки | [datasets/ready/navigation_problem_tracks/](datasets/ready/navigation_problem_tracks/) | ~82k точек |
| Reference | [datasets/ready/reference/](datasets/ready/reference/) | матчинг госномер ↔ SKAI id |

Период видео-пака: `2026-05-12` … `2026-05-19` (выборка Drowsiness/Smoking с video_count>0).

## Найденные типы событий (14)

Из реальной колонки `Type`. Полный канонический справочник — [data/analysis/alarm_types.json](data/analysis/alarm_types.json).

| Raw | Канон. код | Источник | Видео | Severity | Кол-во |
|---|---|---|---|---|---|
| Drowsiness | DMS_DROWSY | DMS (ch5) | ✅ | critical | 15 |
| Smoking | DMS_SMOKING | DMS (ch5) | ✅ | medium | 12 |
| Distraction | DMS_PHONE | DMS | ✅ | high | 4 |
| NoDriver | DRIVER_SUBSTITUTION | DMS | ✅ | high | 4 |
| DangerousDistance | ADAS_HMW | ADAS | ✅ | high | 3 |
| Yawning | DMS_YAWNING | DMS | ✅ | medium | 3 |
| SeatBelt | DMS_SEATBELT | DMS | ✅ | medium | 3 |
| SharpAcceleration | HARSH_ACCEL | TELEMATICS | — | medium | 2 |
| SharpBraking | HARSH_BRAKING | TELEMATICS | ✅ | high | 2 |
| CollisionWarning | ADAS_FCW | ADAS | ✅ | high | 2 |
| Sabotage | CAMERA_TAMPER | DMS | ✅ | high | 1 |
| PedestrianWarning | ADAS_PCW | ADAS | ✅ | high | 1 |
| SpeedLimitViolation | OVERSPEED | COMBINED | — | high | 1 |
| SharpLeftTurn | HARSH_CORNERING | TELEMATICS | ✅ | medium | 1 |

Корреляция канал → тип (подтверждает источник): **ch5 — салонная DMS** (Drowsiness 13, Smoking 12,
NoDriver 4), **ch1–3 — дорожные/ADAS**. Это даёт надёжное правило отнесения видео к `cam_dms_url` (ch5)
vs `cam_front_url` (ch1).

## Как ложатся реальные данные на схему UI

UI потребляет богатую схему инцидента (см. [data/mock/incidents.py](data/mock/incidents.py)):
`id, alarm_type, vehicle_plate, vehicle_model, driver, ts, speed_kmh, risk_level, score, status,
video_available, cam_front_url, cam_dms_url, cameras[], telemetry[], …`.

Реальный CSV даёт **только часть**. Маппинг:

| Поле UI | Откуда брать | Статус |
|---|---|---|
| `id` | `AlarmId` | ✅ есть |
| `alarm_type` | `Type` → canonical (alarm_types.json) | ✅ есть |
| `ts` | `Begin` | ✅ есть |
| `vehicle_plate` | `UnitStateNumber` | ✅ есть |
| `speed_kmh` | `Speed` | ✅ есть (15–107, avg 55) |
| `lat/lon` | ⚠️ в алярмах **пусто** → брать из `track_points` (там есть) | ⚠️ join |
| `address` | `Address` (часто пусто) | ⚠️ редко |
| `video_available` | `VideoCount>0` (у всех 54 = true) | ✅ есть |
| `cam_dms_url` | `video_files` где `channel==5` | ✅ join |
| `cam_front_url` | `video_files` где `channel in (1,2,3)` | ✅ join |
| `telemetry[]` | `track_points` (speed_kmh, angle по времени) | ✅ join |
| `mileage / длительность` | `track_summary` | ✅ join |
| `driver`, `driver_id` | — нет в данных | ❌ enrich/mock |
| `vehicle_model` | — нет (только госномер) | ❌ enrich/mock |
| `risk_level`, `score` | — нет | ❌ вычислять (severity + speed + ночь) |
| `status` | — нет (состояние диспетчера) | ❌ runtime/output |
| `evidence_summary` | — нет | ❌ генерировать из типа |
| `continuous_driving_min`, `is_night` | — нет напрямую | ⚠️ выводимо из времени/треков |

## Ключевые поля, которых нет в данных (нужен enrichment)

1. **Водитель** (`driver`, `driver_id`) — данных о водителях в датасете нет вообще. Нужен
   справочник/мок либо интеграция RFID.
2. **Risk score / risk_level** — нет. Вычислять детерминированно: `severity(тип)` + превышение
   скорости (`Speed` vs лимит 90) + ночное время (`Begin`).
3. **Статус инцидента** — состояние рабочего процесса, пишется в [output/actions.csv](output/), а не в данные.
4. **Координаты алярма** — в `selected_video_alarms` пусты; реальные координаты лежат в
   `track_points`. Сейчас [data_loader.py](backend/data_loader.py) подставляет моковые по городу из `Address`.
5. **vehicle_model** — есть только госномер.

## Рекомендация: как организовать данные для бэкенда

Текущий `load_or_mock` сводит CSV к плоскому `selected_video_alarms` и подменяет колонки. Это
хрупко. Предлагаемая организация:

1. **Слой нормализации** — построить «view-model инцидента» один раз при загрузке:
   `incident = join(selected_video_alarms, video_files[by alarm_id], track_summary, track_points)`
   и обогатить вычисляемыми полями (canonical type, source, severity, risk score, cam_*_url по каналу).
   Это даёт ту же схему, что ждёт UI, но из реальных данных.
2. **Справочник типов** вынести в [data/analysis/alarm_types.json](data/analysis/alarm_types.json)
   (создан) и подключить в [backend/constants.py](backend/constants.py) вместо хардкода —
   единый источник label/source/severity/requires_video.
3. **Видео по каналу**: `ch5 → cam_dms_url`, `ch1 → cam_front_url`, остальные каналы — в список
   `cameras[]`. `media_relative_path` уже указывает на реальные mp4.
4. **Координаты**: приоритет `track_points` (реальные) → fallback на city-jitter из `Address`.
5. **Enrichment-слой** (driver/model/score) держать отдельным, помеченным как синтетический,
   чтобы при появлении реальных справочников его легко заменить.

## Риски при подключении реальных данных

1. **Нет данных о водителях** — досье водителя/звонок водителю работают только на моке.
2. **Координаты алярмов отсутствуют** — карта без join к `track_points` показывает фейковые точки.
3. **`Address` почти всегда пустой** — текстовая локация ненадёжна.
4. **Risk/score синтетические** — нет ground-truth скоринга; нужно зафиксировать формулу.
5. **Выборка смещена** — пак отфильтрован по Drowsiness/Smoking с video>0; распределение типов
   не репрезентативно для реального парка.
6. **Видео — статические mp4-файлы**, не стрим; «±30 сек от события» ограничено длиной клипа
   (~10–12 сек в датасете).

## Созданные/обновлённые артефакты

- [data/analysis/alarm_types.json](data/analysis/alarm_types.json) — канонический справочник 14 типов.
- [DATASET_ANALYSIS.md](DATASET_ANALYSIS.md) — этот отчёт.
