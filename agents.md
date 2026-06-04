# 05. Единое окно видео и телематики

## Goal

Сделать MVP интерфейса, который показывает ценность объединения телематики и видео в одном окне: событие, трек, контекст, медиа-доказательство и быстрое действие.

Строим рабочий оффлайн-прототип. Не оверинжинирить.

## Inputs

- `data/selected_video_alarms.csv` - события VA: аларм, машина, время, тип, скорость, координаты при наличии.
- `data/video_files.csv` - скачанные MP4 и метаданные: `alarm_id`, `video_file_id`, `channel`, `media_relative_path`, размер, длительность.
- `data/track_summary.csv`, `data/track_periods.csv`, `data/track_points.csv`, `data/max_speed_points.csv` - телеметрия вокруг аларма для единого окна.
- `data/vehicles.csv` - сводка по машинам.
- `data/work_rest_single_vehicle/` - отдельный one-object поднабор для режима труда/отдыха.
- MP4 лежат в `../../datasets/media/video_events/`; `media_relative_path` относителен к корню распакованного архива/проекта.

## Outputs

- `output/incident_reports.csv` - сформированные комплексные отчеты.
- `output/actions.csv` - пометить как проверено, запросить видео, создать отчет.
- Опционально `output/incident_report.md` или `output/incident_report.html`.

## Must-have user flows

1. Dispatcher opens telematics event and sees linked video evidence, nearby track rows, speed/coordinates and reason for match.
2. Dispatcher selects incident and creates a short combined report with telemetry plus video references.

## Nice-to-have

- Trip video dossier.
- REB/GPS anomaly check using video-derived hints.
- Timeline view.
- Up to 10 scenario cards showing product value.

## Non-goals

- No real video streaming service.
- No map server dependency.
- No production incident workflow.
- No external API without offline fallback.

## Demo script

1. Show list of enriched events.
2. Open one speeding/harsh driving/geofence event.
3. Show matching video row and local media path/preview.
4. Generate incident report and show saved output.

## Acceptance criteria

- At least one matching rule links telemetry and video by vehicle/time window.
- Details page explains why video was linked.
- Report/action is written to output.
- UI demonstrates time saved versus separate systems.
- README explains local launch.

## Timebox tips

- Use tables and timelines before fancy maps.
- Media path text is acceptable if video preview costs too much time.
- Focus on "one event -> complete context -> action".
- Do not build a video platform.

## AI Tooling & Model Policy

Ограничений на модели нет — используйте наиболее способные доступные модели
(например, Claude Opus). Параллельный запуск нескольких агентов разрешён.

Контекстная гигиена (по-прежнему полезна):

- Не вставляйте в контекст целые репозитории, большие CSV, сырые медиа или сгенерированный вывод без нужды.
- Читайте только файлы, нужные для текущего шага; резюмируйте перед открытием нового контекста.
- Предпочитайте конкретные задачи: один баг, один экран, одно правило, один CSV-трансформ.
- Держите сырые данные локально. Не загружайте приватные датапаки, токены, ключи и секреты во внешние сервисы.

## Implementation Constraints

- Keep the default stack simple: Python 3.12 unless a different stack is deliberately accepted as-is.
- Work offline by default: local CSV files and local media folders.
- Do not integrate with real SKAI production services in the prototype.
- Do not call CRUD/action APIs against real systems unless explicitly approved.
- Avoid microservices, Kubernetes, complex queues, custom auth, background workers, and platform rewrites.
- Prioritize working user flows, explainable logic, a value metric, and an action saved to `output/`.
