# 05. Единое окно видео и телематики

## Goal

Сделать MVP интерфейса, который показывает ценность объединения телематики и видео в одном окне: событие, трек, контекст, медиа-доказательство и быстрое действие.

Строим рабочий оффлайн-прототип за 8 часов. Не оверинжинирить.

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

Use Cherry Studio + OpenRouter as the default AI access layer.

Recommended models:
- Kimi K2.5 - default model for coding and code-agent work.
- Devstral - backup model for coding if Kimi gets stuck.
- Qwen - product analysis, requirements, decomposition, metrics, demo script.
- gpt-oss / OSS/free models - drafts, quick ideas, rewriting, simple explanations.

Do not use expensive models as the default.
Do not use Gemini for this hackathon setup.
Do not run multiple code agents in parallel on the same team API key unless explicitly approved.

Model usage rule:
- Simple code edits: use gpt-oss/free or a cheap model first.
- Main coding: use Kimi K2.5.
- If Kimi fails: try Devstral.
- Product/analytics work: use Qwen.
- If a single request becomes expensive or too slow, stop and reduce context.

## Cost & Context Rules

- Team budget is limited: target roughly $40-50 total AI spend per team.
- Do not use expensive models for continuous repository scanning.
- Do not paste entire repositories, large CSV files, raw media, or generated outputs into the model context.
- Read only the files needed for the current step; summarize findings before opening more context.
- Prefer small prompts with concrete tasks: one bug, one screen, one rule, one CSV transform.
- Stop long agent loops early. If the agent is guessing, reduce scope and provide the exact file/function.
- Keep raw data local. Do not upload private datapacks, tokens, keys, or production-like secrets to AI tools.

## Implementation Constraints

- Build an 8-hour MVP, not a production system.
- Keep the default stack simple: Python 3.12 + Streamlit unless the team deliberately accepts another stack as-is.
- Work offline by default: local CSV files and local media folders.
- Do not integrate with real SKAI production services in the MVP.
- Do not call CRUD/action APIs against real systems unless explicitly approved by organizers.
- Avoid microservices, Kubernetes, complex queues, custom auth, background workers, and platform rewrites.
- Prioritize two working user flows, explainable logic, a value metric, and a demo-ready action saved to `output/`.
