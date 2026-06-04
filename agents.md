# 05. Единое окно видео и телематики

## Goal

Разработать **полноценные экраны-приложения для демонстрации клиенту**, которые показывают ценность
объединения телематики и видео в одном окне: событие, трек, контекст, медиа-доказательство и быстрое действие.

Цель — продукт демо-качества (не черновик-MVP). **Ограничений по стеку и времени нет** — хакатон позади.
Делаем добротно: рабочие сценарии, чистая архитектура по `prompts/v2-fullstack/`. Демо работает на
локальных данных (`datasets/ready/` + DuckDB), без зависимости от прод-сервисов SKAI.

## Implementation plan

Действующий план разработки — **`prompts/v2-fullstack/`** (стек DuckDB + FastAPI + React).
Источник истины по данным/API/токенам — **`prompts/v2-fullstack/00-CONTRACT.md`** (включая §7
full-scope). Каждый агент кодит против контракта, треки D ‖ B ‖ F идут параллельно; порядок волн —
`init/playbook/00-day-plan.md`.

Скоуп — **полный продукт (10 идей, P0+P1+P2)** с **реальной интеграцией** голоса/NLU и справочника
водителей: STT `faster-whisper large-v3`, NLU Groq LLaMA 3.3 70B (fallback regex), детерминированный
`driver_reference` (контракт §7.1, заменяемый на внешний источник). Старая Streamlit-эра — в `prompts/legacy/`.

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

## Demo quality bar

- Цель — экраны демо-качества для показа клиенту: чистый UI по дизайн-системе, реальные данные, рабочие сценарии.
- Видео — реальные MP4 из `datasets/media/` (превью/плеер), не текстовая заглушка пути.
- Держать фокус: "одно событие → полный контекст → действие"; но довести до законченного вида, не до черновика.
- Это не платформа стриминга видео — демонстрационное приложение поверх готовых данных.

## AI Tooling & Model Policy

Ограничений на модели нет — используйте наиболее способные доступные модели
(например, Claude Opus). Параллельный запуск нескольких агентов разрешён.

Контекстная гигиена (по-прежнему полезна):

- Не вставляйте в контекст целые репозитории, большие CSV, сырые медиа или сгенерированный вывод без нужды.
- Читайте только файлы, нужные для текущего шага; резюмируйте перед открытием нового контекста.
- Предпочитайте конкретные задачи: один баг, один экран, одно правило, один CSV-трансформ.
- Держите сырые данные локально. Не загружайте приватные датапаки, токены, ключи и секреты во внешние сервисы.

## Implementation Constraints

- Стек — по `prompts/v2-fullstack/`: DuckDB + FastAPI (Python 3.12) + React/Vite/Tailwind. Ограничений по стеку/времени нет.
- Демо работает на локальных данных: `datasets/ready/` (CSV→DuckDB) + `datasets/media/` (MP4). Не интегрироваться с прод-сервисами SKAI.
- Не вызывать CRUD/action-API реальных систем без явного разрешения (действия пишутся в `output/`).
- Архитектура — добротная и читаемая под демо клиенту; не раздувать инфраструктуру сверх нужд демонстрации (k8s/очереди/own-auth не требуются, но и не запрещены, если оправданы).
- Приоритет: рабочие сценарии, объяснимая логика, метрика ценности, законченный вид экранов.


---

## Customer Context

> Подробнее: `context/customer-research.md`

**Три клиента:**

**Фомин (PepsiCo, ~200 ТС)** — «39 ДТП в телематике, видео подтвердило 5.
Нужно: CAN-скорость + видео ±30 сек в одном окне.»
→ Блок причины события, единый отчёт для страховой.

**Маслов (Балтика, ~300 ТС)** — «3 машины как 5 точек из-за задвоения терминалов.
Нужно: статус камер сразу, кнопка звонка через DMS.»
→ `cameras[]` с online/offline, ролевой switcher Логист/Диспетчер/Безопасник.

**Оздоев (ГПН, ~800 ТС)** — «Нажал нарушение — должно вылезти видео.»
→ Killer feature: клик на строку в отчёте → VideoPanel рядом.

**Маппинг на данные:**
- 54 реальных алярма в `v_incidents` (видео у всех)
- ch5 → `cam_dms_url` (DMS/Drowsiness/Smoking)
- ch1 → `cam_front_url` (ADAS/дорога)
- `navigation_problem_tracks` → экран Восстановление РЭБ (реальные данные!)
- Нет в данных: `driver`, `vehicle_model`, `risk_score` → enrichment/mock

## Screens

| Route | Screen | Priority | Customer |
|-------|--------|----------|----------|
| `/incidents/:id` | Карточка инцидента | **P0** | Фомин, Маслов, Оздоев |
| `/monitor` | Живой мониторинг | **P0** | Маслов |
| `/report` | Аналитический отчёт | **P0** | Оздоев |
| `/` | Лента событий | P1 | все |
| `/tickets` | Заявки | P1 | Маслов |
| `/alert/:id` | Диспетчерский алерт | P2 | Фомин |
| `/trip/:id` | Досье поездки | P2 | Оздоев |
| `/reb/:id` | Восстановление РЭБ | P2 | Оздоев |

> HTML-мокапы для P0: `ui/Карточка инцидента/`, `ui/Промпт_2_Живой мониторинг /`, `ui/Интерактивнй отчет/`
