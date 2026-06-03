# КАРТА ПРОДУКТА — SKAI Unified Incident Window

> Один документ: все идеи, все промпты, все данные, последовательность.
> Команда 7, Тема 5. Хакатон 21 мая 2026.

---

## ПРИОРИТЕТ ИДЕЙ

```
#1 P0  Единое окно инцидента      → видео + телематика + CAN синхронно
#2 P0  Интерактивный отчёт        → голос/текст → подтверждение → дашборд
       Экран 1 (два варианта)      → лента событий + живой мониторинг
#3 P1  Диспетчерский алерт        → автозапрос видео ±15 сек
#4 P1  Список заявок
#5 P1  Видеодосье рейса
#6 P2  РЭБ-восстановление маршрута
#7 P2  Саботаж камеры (нет промпта)
#8 P2  Карта по ролям (расширение экрана 1)
```

---

## ЭКРАНЫ И ИДЕИ

### Экран 1A — Лента событий
**Клиенты:** Фомин (PepsiCo), Маслов (Балтика)
**Фичи из интервью:**
- Источник события: badge [📹 ВА] / [⚡ Тел] / [⚡📹 Оба] — Фомин: «прыгаем между системами»
- Фильтр «Нет видео» — Фомин: «много событий без видео, надо запрашивать архив»
- **Переключатель роли [🏭 Логист | 🛡 Диспетчер | 🔒 Безопасность]** — Маслов: «логисты видят только телематику»
- 1 ТС = 1 событие (не дублирование терминалов) — Маслов: «3 машины — 5 точек»

| Тип | Файл |
|-----|------|
| 💡 Идея | `hackathon/ideas/01-idea-unified-window.md` + `09-role-based-map.md` |
| 🎨 Claude Design | `design-prompts/claude-design/01-events-feed.md` |
| ⚙️ Dev | `prompts/hackathon/wave-03-screens/P4-03A-events-feed--qwen3.md` |
| 📦 Mock | `data/mock/incidents.json` · `data/mock/events-feed.json` |

---

### Экран 1Б — Живой мониторинг (карта)
**Клиенты:** Маслов (Балтика — логисты)
**Фичи из интервью:**
- Тёмная тема, карта 24/7
- **Переключатель роли** — логисты видят только позицию ТС
- 1 ТС = 1 маркер на карте
- Попап с badge источника + «1 ТС · 1 объект»

| Тип | Файл |
|-----|------|
| 🎨 Claude Design | `design-prompts/claude-design/02-live-monitor.md` |
| ⚙️ Dev | `prompts/hackathon/wave-03-screens/P1-03E-live-monitor--kimi-k2.6.md` |
| 📦 Mock | `data/mock/incidents.json` · `data/mock/live-monitor.json` · `data/mock/vehicles.json` |

---

### Экран 2 — Карточка инцидента с видео **[ИДЕЯ #1 P0]**
**Клиенты:** Фомин (PepsiCo), Оздоев (ГПН)
**Фичи из интервью:**
- Два видеоплеера ADAS+DMS синхронно — Фомин: «CAN правдивее, сравниваем в одном окне»
- CAN-скорость + акселерометр, маркер движется с видео
- Badge источника [⚡📹 Оба] — откуда событие
- **[📹 Позвонить через камеру]** — Маслов: «звонить через регистратор, не по телефону»
- **Блок «Причина события»** — Фомин: «почему резкое торможение — засыпал, подрезали?»
  AI-версия + кнопки [😴 Засыпал] [📱 Отвлёкся] [🚗 Подрезали] [⚙ Техн. сбой]

| Тип | Файл |
|-----|------|
| 💡 Идея | `hackathon/ideas/01-idea-unified-window.md` |
| 🎨 Claude Design | `design-prompts/claude-design/03-idea1-incident-video.md` |
| ⚙️ Dev (экран) | `prompts/hackathon/wave-03-screens/P3-03B-incident-card--kimi-k2.6.md` |
| ⚙️ Dev (компоненты) | `02A-idea1-IncidentCard` · `02B-idea1-VideoPanel` · `02C-idea1-TelemetryChart` · `02D-idea1-ActionButtons` · `02F` · `02G` · `02H` |
| 📦 Mock | `data/mock/incidents.json` · `data/mock/incident-video.json` |

---

### Экран 3 — Карточка инцидента без видео **[ИДЕЯ #1 P0]**
**Клиенты:** Фомин (PepsiCo)
**Фичи:**
- Placeholder с объяснением почему нет видео (CAM-03 offline)
- Кнопка «Запросить архивное видео» → статус запроса
- **[📹 Позвонить через камеру]** — те же состояния
- **Блок «Причина события»** — без видео, только телеметрия

| Тип | Файл |
|-----|------|
| 💡 Идея | `hackathon/ideas/01-idea-unified-window.md` |
| 🎨 Claude Design | `design-prompts/claude-design/04-idea1-incident-no-video.md` |
| ⚙️ Dev (экран) | `prompts/hackathon/wave-03-screens/P3-03B-incident-card--kimi-k2.6.md` |
| 📦 Mock | `data/mock/incidents.json` · `data/mock/incident-no-video.json` |

---

### Экран 4 — Интерактивный аналитический отчёт **[ИДЕЯ #2 P0]**
**Клиенты:** Оздоев (ГПН), Фомин (PepsiCo)
**Фичи:**
- Голосовой ввод 🎤 (faster-whisper large-v3, RU/KK/EN) — или текстом
- Подтверждающее окно «Вот как я понял» + уверенность 96%
- **Режим В-1** (один водитель): карточка + KPI + трек + график + таблица ВА+тел → клик→видео
- **Режим В-2** (парк): toggle [👤 По водителям | 🚛 По ТС]
  - По ТС: камеры online/offline, водители за период (1 ТС = N водителей)
- Колонка «Причина» в таблице нарушений
- Клик на строку → VideoSlidePanel с причиной
- Источник: Оздоев: «Нажал нарушение — вылезло видео»

| Тип | Файл |
|-----|------|
| 💡 Идея | `hackathon/ideas/02-idea-interactive-report.md` |
| 🎨 Claude Design | `design-prompts/claude-design/05-idea2-interactive-report.md` |
| ⚙️ Dev (экран) | `prompts/hackathon/wave-03-screens/P2-03D-analytics-screen--kimi-k2.6.md` |
| ⚙️ Dev (компоненты) | `02E-idea2-analytics-components--qwen3.md` (13 компонентов) |
| 📦 Mock В-1 | `data/mock/driver-report.json` — Иванов, 7 нарушений, 487 км |
| 📦 Mock В-2 | `data/mock/fleet.json` · (нужно создать: fleet-report.json, fleet-vehicles.json) |

---

### Экран 5 — Диспетчерский алерт ±15 сек [P1]
**Клиенты:** Оздоев (ГПН) — Богобоязов Павел, Нефедов Вадим
**Фичи:**
- Автозапрос видео ±15 сек при критическом событии
- Алерт поверх экрана (не блокирует работу)
- Роли: Логист видит только badge, Диспетчер — полный алерт
- Связка с диспетчерским центром

| Тип | Файл |
|-----|------|
| 💡 Идея | `hackathon/ideas/08-camera-sabotage.md` |
| 🎨 Claude Design | `design-prompts/claude-design/06-dispatch-alert-plus.md` |
| 📦 Mock | `data/mock/dispatch-alert.json` |

---

### Экран 6 — Список заявок [P1]

| Тип | Файл |
|-----|------|
| 🎨 Claude Design | `design-prompts/claude-design/07-tickets-screen.md` |
| ⚙️ Dev | `prompts/hackathon/wave-05-polish/05A-tickets-table--qwen3.md` · `05B-tickets-screen--qwen3.md` |
| 📦 Mock | `data/mock/tickets.json` |

---

### Экран 7 — Видеодосье рейса [P1]
**Источник:** Бриф организаторов хакатона (сценарий Т+В)

| Тип | Файл |
|-----|------|
| 💡 Идея | `hackathon/ideas/09-role-based-map.md` |
| 🎨 Claude Design | `design-prompts/claude-design/08-trip-dossier.md` |
| 📦 Mock | `data/mock/trip-dossier.json` |

---

### Экран 8 — Восстановление маршрута при РЭБ [P1]
**Источник:** Бриф организаторов

| Тип | Файл |
|-----|------|
| 💡 Идея | `hackathon/ideas/04-competitors-analysis.md` |
| 🎨 Claude Design | `design-prompts/claude-design/09-reb-route-recovery.md` |
| 📦 Mock | `data/mock/reb-route.json` |

---

### Идеи без дизайн-промпта [P2]

| Идея | Источник | Файл идеи | Что нужно |
|------|----------|-----------|-----------|
| Детекция саботажа камеры | Фомин (PepsiCo) | `hackathon/ideas/08-camera-sabotage.md` | Создать `design-prompts/claude-design/ (промпт не создан)` |
| Карта по ролям (полная) | Маслов (Балтика) | `hackathon/ideas/09-role-based-map.md` | Расширить 01/02 или создать `11-role-map.md` |

---

## ПОСЛЕДОВАТЕЛЬНОСТЬ РАЗРАБОТКИ

```
ЧАС 0   Все читают: AGENTS.md + hackathon/ideas/01 + 02

ЧАС 1   ПАРАЛЛЕЛЬНО — Wave 1 (Foundation):
         01A types       01B constants    01C incidents.json
         01D vehicles    01E app shell
         01F-A driver-report.json         (Идея #2 В-1)
         01F-B fleet-reports.json         (Идея #2 В-2, нужно создать)
         01F-C presets + types

ЧАС 2   ПАРАЛЛЕЛЬНО — три потока:

  ПОТОК 1 — Экран 1:
    03A EventFeedScreen       03E LiveMonitorScreen

  ПОТОК 2 — Идея #1 (компоненты):
    02A IncidentCard           02B VideoPanel
    02C TelemetryChart         02D ActionButtons (+звонок +причина)
    02F IncidentTopBar         02G ContextChips
    02H SourceStatusGrid

  ПОТОК 3 — Идея #2 (компоненты):
    02E analytics-components (13 компонентов)
      VoiceQueryBox · ConfirmationModal · DriverReportCard
      ViolationsTable · RouteTrackMap · SpeedChart · VideoSlidePanel
      FleetDriversList · FleetBarChart · FleetMap
      DriverMiniDashboard · FleetVehiclesList · VehicleMiniDashboard

ЧАС 3   ПАРАЛЛЕЛЬНО — экраны P0:
  ПОТОК 2: 03B UnifiedIncidentWindow  (зависит от 02A-H)
  ПОТОК 3: 03D AnalyticsScreen        (зависит от 02E, 01F)

ЧАС 4   04-wire-routing (сходятся все потоки)
         Маршруты: / · /monitor · /incident/:id · /analytics

ЧАС 5   ПАРАЛЛЕЛЬНО — полировка:
         05A tickets-table    05B tickets-screen
         05C smoke-checklist  05D demo-script

ЧАС 5+  Демо по 05D-demo-script--gpt-oss.md:
         Flow 1: inc-002 → видео + телеметрия + [Создать заявку]
         Flow 2: inc-003 → нет видео → [Запросить архив]
         Flow 3: голос «Нарушения Иванова за 3 дня» → подтверждение → отчёт
```

---

## РЕАЛЬНЫЕ ДАННЫЕ (datasets/ready/)

| Файл | Что содержит | Для экранов |
|------|-------------|------------|
| `selected_video_alarms.csv` | 54 аларма: тип, время, скорость, адрес, CameraIds | Все экраны с видео |
| `video_files.csv` | 94 MP4: канал, длительность, media_relative_path | Видеоплееры |
| `track_points.csv` | 81,977 точек: lat, lon, speed_kmh, timestamp | Карты, графики |
| `sensor_graph_points.csv` | 959k точек датчиков | Графики телеметрии |
| `sensor_catalog.csv` | 627 датчиков: id, имя, группа, единицы | Выбор датчиков |
| `reference/*.csv` | Сопоставление id машин между системами | Соединение данных |
| `training/` | 94 MP4 (728 сек) | Видеоплееры |
| `fuel_reconciliation/` | Топливная сверка (30 строк) | Не для темы 5 |
| `navigation_problem_tracks/` | Проблемные треки | Не для темы 5 |

> ⚠️ data/mock/*.json — ПРИМЕРЫ, не соответствующие реальной структуре CSV. НЕ использовать.

---

## КЛЮЧЕВЫЕ ДАННЫЕ ДЛЯ ДЕМО

| Параметр | Значение |
|----------|----------|
| Алармов для демо | 5-10 из selected_video_alarms.csv (разные типы: Sabotage, DMS, ADAS) |
| Точек трека | 50-100 вокруг одного аларма |
| Датчиков для графика | 2-3: скорость (__lgc.spd.0), топливо, обороты |
| MP4 для плеера | 2-4 ролика (каналы 1 и 5) |
| Период | 14-15.05.2026 (видео) / 04-10.05.2026 (датчики/треки) |
| STT | faster-whisper large-v3 (open-source, RU 🇷🇺 / KK 🇰🇿 / EN 🇬🇧) |
| NLU | Groq API + LLaMA 3.3 70B |
| Primary color | #1E3A8A |
| Font | Inter |
