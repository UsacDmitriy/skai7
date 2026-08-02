# 05. Единое окно видео и телематики

## Goal

Разработать полноценные экраны-приложения demo-качества, показывающие ценность
объединения телематики и видео: alarm, трек, контекст, медиадоказательство и
быстрое действие. Демо работает на локальных `datasets/ready/` и DuckDB без
зависимости от production-сервисов SKAI.

## Implementation plan

Действующий план — `prompts/v2-fullstack/` (DuckDB + FastAPI + React). Источник
истины по данным, API и токенам — `prompts/v2-fullstack/00-CONTRACT.md`, включая
§7 full-scope. Порядок волн — `init/playbook/00-day-plan.md`; независимые треки
D, B и F можно вести параллельно.

Скоуп — полный продукт (10 идей, P0+P1+P2) с рабочим голосом/NLU и справочником
водителей: STT `faster-whisper large-v3`, NLU Groq LLaMA 3.3 70B с regex
fallback, детерминированный `driver_reference` по контракту §7.1. Старая
Streamlit-эра хранится в `prompts/legacy/`.

## Inputs

Канонический источник данных — `datasets/ready/` (контракт §3):

- `datasets/ready/video_events/selected_video_alarms.csv` — alarms VA;
- `datasets/ready/video_events/video_files.csv` — MP4 и метаданные;
- `datasets/ready/video_events/track_summary.csv`, `track_periods.csv`,
  `track_points.csv`, `max_speed_points.csv` — телеметрия вокруг alarm;
- `datasets/ready/video_events/vehicles.csv` — сводка по машинам;
- `datasets/ready/video_events/work_rest_single_vehicle/` — one-object набор;
- MP4 — в `datasets/media/video_events/`, пути из данных относительны к корню
  распакованного архива/проекта.

## Outputs

- `output/incident_reports.csv` — комплексные отчёты;
- `output/actions.csv` — проверить, запросить видео, создать отчёт;
- опционально `output/incident_report.md` или `.html`.

## Must-have user flows

1. Диспетчер открывает alarm и видит связанное видео, соседние точки трека,
   скорость, координаты и объяснение связи.
2. Диспетчер создаёт краткий объединённый отчёт с телематикой и ссылками на
   видео.

## Acceptance and demo quality

- Минимум одно правило связывает телематику и видео по машине/временному окну.
- Детальная страница объясняет, почему видео связано с alarm.
- Отчёт или действие сохраняется в `output/`.
- UI демонстрирует экономию времени относительно отдельных систем.
- README описывает локальный запуск.
- Используются реальные MP4, а не текстовые заглушки путей.
- Основной сценарий: один alarm → полный контекст → действие.

Nice-to-have: досье поездки, проверка REB/GPS-аномалии, timeline и до десяти
карточек сценариев. Не входят в цель: production incident workflow, сервер
стриминга, зависимость от внешнего map server или внешний API без offline
fallback.

## Context hygiene

- Не передавать целые репозитории, большие CSV, сырые медиа или сгенерированный
  вывод без необходимости.
- Читать только файлы текущего шага и резюмировать контекст перед переходом.
- Держать приватные датапаки, токены, ключи и секреты локально.
- AI execution/model policy находится в `AGENTS.md`.

## Implementation constraints

- Стек: DuckDB + FastAPI (Python 3.12) + React/Vite/Tailwind.
- Демо использует локальные CSV/DuckDB и MP4; production SKAI не затрагивается.
- CRUD/action API реальных систем запрещены без явного разрешения; действия
  пишутся в `output/`.
- Архитектура должна быть понятной и demo-ready без неоправданного раздувания
  инфраструктуры.

## Customer context

Подробнее: `context/customer-research.md`.

- Фомин (PepsiCo, ~200 ТС): CAN-скорость + видео ±30 сек в одном окне, блок
  причины alarm и единый отчёт для страховой.
- Маслов (Балтика, ~300 ТС): статусы камер, DMS-звонок, `cameras[]` с
  online/offline, переключатель ролей.
- Оздоев (ГПН, ~800 ТС): клик на нарушение сразу показывает видео; VideoPanel
  рядом с отчётом.

Данные: 54 реальных alarms в `v_incidents`; `ch5` — DMS, `ch1` — ADAS/дорога,
`navigation_problem_tracks` — REB. `driver`, `vehicle_model`, `risk_score`
отсутствуют и требуют enrichment/mock.

## Screens

| Route | Screen | Priority |
|---|---|---|
| `/incidents/:id` | Карточка инцидента | P0 |
| `/monitor` | Живой мониторинг | P0 |
| `/report` | Аналитический отчёт | P0 |
| `/` | Лента alarms | P1 |
| `/tickets` | Заявки | P1 |
| `/alert/:id` | Диспетчерский alarm | P2 |
| `/trip/:id` | Досье поездки | P2 |
| `/reb/:id` | Восстановление REB | P2 |

HTML-мокапы P0: `ui/03 Карточка инцидента/`, `ui/02 Живой мониторинг/`,
`ui/05 Интерактивный отчёт/`.
