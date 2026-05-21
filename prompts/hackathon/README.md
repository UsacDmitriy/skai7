# prompts/hackathon — Плейбук запуска промптов

> 🖥 **Инструмент:** Cherry Studio → OpenRouter (team key)
> 💰 **Бюджет команды:** $50 · Реальный расход: ~$1.50
> ⏱ **8 часов** · 5 волн · **32 промпта**
>
> **Формат имён:** `{приоритет}-{номер}-{название}--{модель}.md` — модель видна из имени.
> **Правило:** дизайн-спека встроена в промпт — HTML-файлы из `code/clade_design/` НЕ читать.

---

## 🗺 КАРТА ПАРАЛЛЕЛЬНОГО ЗАПУСКА

```
09:30 ──────────────────── 00 ──── nemotron (1 промпт)
│
09:45 ──────────────────── 00a ─── kimi + qwen3 (3 промпта)
│         ┌─ 00a-A (kimi) ──→ TECH-DESIGN.md ──┐
│         │                                      ├─ 00a-B (kimi)
│         └─ 00a-C (qwen3) ──→ constants draft ─┘
│
10:30 ──────────────────── 01 ──── qwen3 (9 промптов)
│         ┌─ 01A ── types.ts ────────────────────┐
│         ├─ 01C ── incidents.json ──────────────┤ все параллельно
│         ├─ 01D ── vehicles.json ───────────────┤ (разные выходы)
│         ├─ 01F-A ── driver-report.json ────────┤
│         └─ 01F-B ── fleet-report.json ─────────┘
│              │ (ждём 01A)
│         ┌─ 01B ── constants.ts
│         ├─ 01F-C ── analyticsPresets.ts
│         └─ 01F-D ── fleet-vehicles.json
│              │ (ждём 01A + 01B)
│         └─ 01E ── App.tsx + конфиги
│
11:30 ──────────────────── 02 ──── qwen3 (9 промптов, ВСЕ параллельно)
│         ├─ 02A IncidentCard       ├─ 02E VoiceQueryBox (сессия 1)
│         ├─ 02B VideoPanel         ├─ 02E ConfirmationModal (сессия 2)
│         ├─ 02C TelemetryChart     ├─ 02E DriverReportCard (сессия 3)
│         ├─ 02D ActionButtons      ├─ 02E ViolationsTable (сессия 4)
│         ├─ 02F IncidentTopBar     ├─ 02E RouteTrackMap (сессия 5)
│         ├─ 02G ContextChips       ├─ 02E SpeedChart (сессия 6)
│         └─ 02H SourceStatusGrid   └─ 02E VideoSlidePanel (сессия 7)
│                                      02E FleetDriversList (сессия 8)
│                                      02E FleetBarChart (сессия 9)
│                                      02E FleetMap (сессия 10)
│                                      02E DriverMiniDashboard (сессия 11)
│                                      02E FleetVehiclesList (сессия 12)
│                                      02E VehicleMiniDashboard (сессия 13)
│
13:30 ──────────────────── 03 ──── kimi + qwen3 (5 промптов)
│         P1 (kimi) ──→ LiveMonitorScreen ── главный экран
│              │
│         P2 (kimi) ──→ AnalyticsScreen ──── интерактивный отчёт
│              │
│         P3 (kimi) ──→ IncidentCard ─────── карточка инцидента
│              │
│         P4 (qwen3) ──→ EventFeedScreen ─── лента (параллельно с P1-P3)
│         P5 (qwen3) ──→ KPIBar ──────────── (параллельно с P1-P3)
│
14:30 ──────────────────── 04 ──── qwen3 (1 промпт)
│         замена заглушек в App.tsx на реальные экраны
│
14:45 ──────────────────── 05 ──── qwen3 + nemotron + gpt-oss (4 промпта)
│         ├─ 05A + 05B (qwen3) ── параллельно
│         └─ 05C (nemotron) + 05D (gpt-oss) ── параллельно
```

---

## 🚀 Подготовка Cherry Studio (08:45–09:00)

1. Открыть Cherry Studio → Settings → Model Providers → OpenRouter → вставить team key
2. Добавить модели:
   - `qwen/qwen3-coder:free` — кодинг (бесплатно, 200 req/day)
   - `moonshotai/kimi-k2.6` — архитектура + P0-экраны (~$0.065/запрос)
   - `nvidia/nemotron-3-super-120b-a12b:free` — контекст
   - `openai/gpt-oss-120b:free` — текст/демо
3. Создать новую сессию (Cmd+N) → выбрать модель → вставить промпт → Enter
4. После каждого ответа агента: скопировать код в проект, `npm run build`, проверить ошибки

---

## 🌊 ВОЛНА 00 — Контекст (09:30–09:45)

**Цель:** агент читает проект и проверяет понимание.

| # | Промпт | Модель | Передать | Выход | Цена |
|---|--------|--------|----------|-------|------|
| 1 | `wave-00/00-read-context--nemotron.md` | nemotron:free | только промпт | ответ по шаблону | $0 |

**Как запускать:** 1 сессия. Скопировать промпт целиком, модель nemotron, Enter.

**Что передать:** НИЧЕГО дополнительно. В промпте уже сказано «Прочитай AGENTS.md». Агент сам прочитает файл.

**Чекпоинт 00:** агент правильно назвал 5 mock-кейсов (госномер + ФИО + тип), перечислил ≥7 компонентов, назвал цвета.

---

## 🌊 ВОЛНА 00A — Архитектура (09:45–10:30)

**Цель:** создать TECH-DESIGN.md, черновики types.ts и constants.ts.

### Шаг 1 — Архитектура (1 сессия, kimi)

| # | Промпт | Модель | Передать | Выход | Цена |
|---|--------|--------|----------|-------|------|
| 2 | `wave-00a-architecture/00a-A-tech-design--kimi-k2.6.md` | kimi-k2.6 | секции 1,5,6 из AGENTS.md + прикрепить verify-standalone.jpg как image | `hackathon/context/TECH-DESIGN.md` | ~$0.032 |

**Как запускать:**
1. Скопировать секции 1, 5, 6 из AGENTS.md в начало сессии
2. Прикрепить `code/clade_design/Интерактивнй отчет/verify-standalone.jpg` как image (НЕ как текст!)
3. Вставить промпт, Enter

### Шаг 2 — Параллельно (2 сессии)

| # | Промпт | Модель | Передать | Выход | Цена |
|---|--------|--------|----------|-------|------|
| 3 | `wave-00a-architecture/00a-B-data-contract--kimi-k2.6.md` | kimi-k2.6 | TECH-DESIGN.md + `data/mock/incidents.json` + `data/mock/driver-report.json` | **черновик** `code/frontend/src/types.ts` | ~$0.034 |
| 4 | `wave-00a-architecture/00a-C-design-tokens--qwen3.md` | qwen3:free | прикрепить verify-standalone.jpg как image | **черновик** `code/frontend/src/constants.ts` | $0 |

> ⚠️ Сессию #3 запускать ПОСЛЕ #2 — нужен TECH-DESIGN.md.
> Сессия #4 — независима, можно параллельно с #2.

**Чекпоинт 00A:** в проекте есть `hackathon/context/TECH-DESIGN.md`, черновики `types.ts` и `constants.ts`.

---

## 🌊 ВОЛНА 01 — Foundation (10:30–11:30)

**Цель:** финальные `types.ts`, `constants.ts`, `App.tsx`, конфиги и ВСЕ mock JSON-файлы.

**Модель:** все 9 промптов — `qwen/qwen3-coder:free` ($0).

### Группа A — независимые (5 сессий, ЗАПУСТИТЬ ОДНОВРЕМЕННО)

Эти промпты не зависят друг от друга. Открыть 5 вкладок Cherry Studio, запустить разом.

| # | Промпт | Передать доп. контекст | Выходной файл |
|---|--------|----------------------|--------------|
| 5 | `wave-01-foundation/01A-types--qwen3.md` | `data/mock/incidents.json` (поля должны совпадать) | `code/frontend/src/types.ts` |
| 6 | `wave-01-foundation/01C-incidents-json--qwen3.md` | `data/mock/incidents.json` | `data/mock/incidents.json` (обновить) |
| 7 | `wave-01-foundation/01D-vehicles-json--qwen3.md` | `data/mock/incidents.json` | `data/mock/vehicles.json` |
| 8 | `wave-01-foundation/01F-A-driver-report--qwen3.md` | только промпт | `data/mock/driver-report.json` |
| 9 | `wave-01-foundation/01F-B-fleet-reports--qwen3.md` | только промпт | `data/mock/fleet-report.json` (⚠️ также создаст `fleet-vehicles.json`) |

> ⚠️ #9 создаёт и `fleet-report.json` и `fleet-vehicles.json`. Не запускать параллельно с #12 (01F-D) — оба пишут `fleet-vehicles.json`.

### Группа B — после 01A (3 сессии параллельно)

Дождаться завершения #5 (types.ts готов). Открыть 3 вкладки, запустить разом.

| # | Промпт | Передать доп. контекст | Выходной файл |
|---|--------|----------------------|--------------|
| 10 | `wave-01-foundation/01B-constants--qwen3.md` | `code/frontend/src/types.ts` + `hackathon/context/DESIGN.md` | `code/frontend/src/constants.ts` |
| 11 | `wave-01-foundation/01F-C-presets-types--qwen3.md` | `code/frontend/src/types.ts` + AGENTS.md | `code/frontend/src/analyticsPresets.ts` |
| 12 | `wave-01-foundation/01F-D-fleet-vehicles--qwen3.md` | только промпт | `data/mock/fleet-vehicles.json` |

> ⚠️ #12 и #9 — конфликт на `fleet-vehicles.json`. Запускать последовательно: сначала #9, потом #12. Или: в #9 попросить агента создать ТОЛЬКО `fleet-report.json`.

### Группа C — после 01A + 01B (1 сессия)

| # | Промпт | Передать | Выход |
|---|--------|----------|-------|
| 13 | `wave-01-foundation/01E-app-infra--qwen3.md` | `code/frontend/src/types.ts` + `code/frontend/src/constants.ts` + секция routing из TECH-DESIGN.md | `App.tsx` + `tailwind.config.js` (тема) |

**Чекпоинт 01:** `npm run dev` → :5173 открывается. `ls code/frontend/src/*.ts` → types.ts + constants.ts + analyticsPresets.ts существуют. `ls data/mock/*.json` → ≥10 файлов.

---

## 🌊 ВОЛНА 02 — Компоненты (11:30–13:00)

**Цель:** 20 компонентов React. Все файлы — `qwen/qwen3-coder:free` ($0).

**Передавать с каждым промптом:** `code/frontend/src/types.ts` + `code/frontend/src/constants.ts` (оба файла маленькие, ~1.7K токенов вместе).

### Поток 1 — Идея #1: Единое окно инцидента (7 сессий параллельно)

| # | Промпт | Компонент | Назначение |
|---|--------|-----------|-----------|
| 14 | `wave-02-components/02A-idea1-IncidentCard--qwen3.md` | `IncidentCard.tsx` | Карточка в ленте |
| 15 | `wave-02-components/02B-idea1-VideoPanel--qwen3.md` | `VideoEvidencePanel.tsx` | Видеоплеер ADAS+DMS |
| 16 | `wave-02-components/02C-idea1-TelemetryChart--qwen3.md` | `TelemetryChart.tsx` | Recharts скорость+акселерометр |
| 17 | `wave-02-components/02D-idea1-ActionButtons--qwen3.md` | `ActionButtons.tsx` | Кнопки действий |
| 18 | `wave-02-components/02F-idea1-IncidentTopBar--qwen3.md` | `IncidentTopBar.tsx` | Шапка карточки |
| 19 | `wave-02-components/02G-idea1-ContextChips--qwen3.md` | `ContextChips.tsx` | Чипы контекста |
| 20 | `wave-02-components/02H-idea1-source-status-grid--qwen3.md` | `SourceStatusGrid.tsx` | Статус камер |

### Поток 2 — Идея #2: Интерактивный отчёт (13 сессий НЕ параллельно)

Промпт `02E-idea2-analytics-components--qwen3.md` генерирует 13 компонентов. Это ОДИН промпт, но Cherry Studio запускает его 13 РАЗ — каждый раз для отдельного компонента.

**Как запускать:** каждый раз копировать ОДИН И ТОТ ЖЕ промпт, но в начале сессии писать «Создай компонент [ИМЯ]. Следуй инструкции ниже.» — и вставлять промпт.

| # | Имя компонента | Файл |
|---|---------------|------|
| 21 | VoiceQueryBox | `analytics/VoiceQueryBox.tsx` |
| 22 | ConfirmationModal | `analytics/ConfirmationModal.tsx` |
| 23 | DriverReportCard | `analytics/DriverReportCard.tsx` |
| 24 | ViolationsTable | `analytics/ViolationsTable.tsx` |
| 25 | RouteTrackMap | `analytics/RouteTrackMap.tsx` |
| 26 | SpeedChart | `analytics/SpeedChart.tsx` |
| 27 | VideoSlidePanel | `analytics/VideoSlidePanel.tsx` |
| 28 | FleetDriversList | `analytics/FleetDriversList.tsx` |
| 29 | FleetBarChart | `analytics/FleetBarChart.tsx` |
| 30 | FleetMap | `analytics/FleetMap.tsx` |
| 31 | DriverMiniDashboard | `analytics/DriverMiniDashboard.tsx` |
| 32 | FleetVehiclesList | `analytics/FleetVehiclesList.tsx` |
| 33 | VehicleMiniDashboard | `analytics/VehicleMiniDashboard.tsx` |

**Оптимизация:** поток 1 и поток 2 НЕЗАВИСИМЫ — можно запускать параллельно (7 сессий идеи #1 + 13 сессий идеи #2 одновременно, если хватает вкладок Cherry Studio).

**Чекпоинт 02:** `ls code/frontend/src/components/*.tsx code/frontend/src/components/analytics/*.tsx | wc -l` → ≥20. `npm run build` — без ошибок.

---

## 🌊 ВОЛНА 03 — Экраны (13:30–14:30)

**Цель:** 5 экранов — собрать компоненты в страницы.

### P1–P3: Главные экраны (kimi-k2.6, ПОСЛЕДОВАТЕЛЬНО)

Эти три промпта используют kimi-k2.6 (~$0.065–0.070 каждый). Запускать строго по очереди: сначала P1, дождаться → P2, дождаться → P3.

| # | Порядок | Промпт | Экран | Передать | Цена |
|---|---------|--------|-------|----------|------|
| 34 | **#1** | `wave-03-screens/P1-03E-live-monitor--kimi-k2.6.md` | `LiveMonitorScreen.tsx` — **главный экран** | `types.ts` + промпт | ~$0.062 |
| 35 | **#2** | `wave-03-screens/P2-03D-analytics-screen--kimi-k2.6.md` | `AnalyticsScreen.tsx` — интерактивный отчёт | `types.ts` + `analyticsPresets.ts` + промпт | ~$0.070 |
| 36 | **#3** | `wave-03-screens/P3-03B-incident-card--kimi-k2.6.md` | `UnifiedIncidentWindow.tsx` — карточка инцидента | `types.ts` + промпт | ~$0.068 |

> ⚠️ Дизайн-спека УЖЕ встроена в каждый промпт. НЕ читать HTML-файлы из `code/clade_design/`.

### P4–P5: Вспомогательные экраны (qwen3:free, параллельно с P1–P3)

Эти два промпта можно запустить в любой момент во время волны 03, они не зависят от P1–P3.

| # | Промпт | Экран | Передать | Цена |
|---|--------|-------|----------|------|
| 37 | `wave-03-screens/P4-03A-events-feed--qwen3.md` | `EventFeedScreen.tsx` | AGENTS.md + `02-live-monitor.md` | $0 |
| 38 | `wave-03-screens/P5-03C-kpi-bar--qwen3.md` | `KPIBar.tsx` | `types.ts` + `constants.ts` | $0 |

**Чекпоинт 03:** `:5173` — LiveMonitorScreen открывается, можно провалиться в AnalyticsScreen → IncidentCard.

---

## 🌊 ВОЛНА 04 — Роутинг (14:30–14:45)

**Цель:** заменить заглушки в App.tsx на реальные экраны.

| # | Промпт | Модель | Передать | Цена |
|---|--------|--------|----------|------|
| 39 | `wave-04-routing/04-routing--qwen3.md` | qwen3:free | текущий `App.tsx` + секция routing из TECH-DESIGN.md | $0 |

**Чекпоинт 04:** все маршруты работают: `/`, `/monitor`, `/incident/:id`, `/analytics`, `/tickets`.

---

## 🌊 ВОЛНА 05 — Полировка (14:45–15:30)

| # | Промпт | Модель | Передать | Выход | Цена |
|---|--------|--------|----------|-------|------|
| 40 | `wave-05-polish/05A-tickets-table--qwen3.md` | qwen3:free | `types.ts` + `constants.ts` | `TicketsTable.tsx` | $0 |
| 41 | `wave-05-polish/05B-tickets-screen--qwen3.md` | qwen3:free | `types.ts` + `constants.ts` | `TicketsScreen.tsx` | $0 |
| 42 | `wave-05-polish/05C-smoke-checklist--nemotron.md` | nemotron:free | только промпт | чеклист (текст) | $0 |
| 43 | `wave-05-polish/05D-demo-script--gpt-oss.md` | gpt-oss:free | `hackathon/playbook/02-pitch-template.md` | `hackathon/PITCH.md` | $0 |

**Запуск:** #40+#41 параллельно. #42+#43 параллельно.

**Чекпоинт 05:** оба Flow работают end-to-end. Flow 1: inc-002 → видео + телеметрия → «Создать заявку». Flow 2: inc-003 → placeholder → «Запросить архив». Flow 3: голос «Нарушения Иванова за 3 дня» → подтверждение → дашборд.

---

## 💰 Бюджет по волнам

| Волна | Промптов | Модели | Цена |
|-------|---------|--------|------|
| 00 | 1 | nemotron:free | $0 |
| 00a | 3 | kimi ×2 + qwen3 ×1 | ~$0.066 |
| 01 | 9 | qwen3:free ×9 | $0 |
| 02 | 9 файлов (20 компонентов) | qwen3:free ×20 | $0 |
| 03 | 5 | kimi ×3 + qwen3 ×2 | ~$0.200 |
| 04 | 1 | qwen3:free | $0 |
| 05 | 4 | qwen3+nemotron+gpt-oss (все free) | $0 |
| **Итого** | **43** | | **~$0.27** |

> Запас: $49.73 из $50. Можно заменить часть qwen3 на kimi-k2.6 для сложных компонентов.

---

## 🔧 Аварийные ситуации

| Ситуация | Действие |
|----------|----------|
| **429 (rate limit) на qwen3:free** | Переключить на `deepseek/deepseek-v4-flash:free`. Если тоже 429 → `deepseek/deepseek-v4-flash` ($0.04/M input, копейки) |
| **kimi-k2.6 ошибка** | Подождать 30 сек, повторить. 3-я ошибка подряд → `deepseek/deepseek-v4-flash` |
| **Все free-модели упали** | Все оставшиеся промпты на `deepseek/deepseek-v4-flash` (~$0.10 за всё) |
| **TypeScript ошибка после промпта** | Копировать ТОЛЬКО файл с ошибкой + первые 30 строк ошибки → qwen3:free «Исправь» |
| **Агент создал не тот файл** | Перезапустить тот же промпт с уточнением «Путь к файлу: [правильный путь]» |
| **Дизайн не совпадает с макетом** | Скопировать секцию «ДИЗАЙН-СПЕКА» из промпта волны 03 + проблемный код → kimi-k2.6 |

---

## ✅ Шпаргалка: что передавать с каждым типом промпта

| Тип промпта | Всегда передавать | Никогда не передавать |
|---|---|---|
| Компоненты (02A–02H) | `types.ts` + `constants.ts` | HTML-файлы, AGENTS.md целиком |
| Аналитика (02E) | `types.ts` + AGENTS.md (секция 4) | HTML-файлы |
| Экраны kimi (P1–P3) | `types.ts` + промпт (дизайн внутри) | HTML-файлы |
| Экраны qwen3 (P4–P5) | `types.ts` + `constants.ts` | HTML-файлы |
| Роутинг (04) | текущий `App.tsx` | — |

---

## 📂 Структура выходных файлов (что должно получиться)

```
code/frontend/src/
  types.ts                          ← 01A
  constants.ts                      ← 01B
  analyticsPresets.ts               ← 01F-C
  App.tsx                           ← 01E → 04
  main.tsx                          ← уже есть
  index.css                         ← уже есть
  components/
    IncidentCard.tsx                ← 02A
    VideoEvidencePanel.tsx          ← 02B
    TelemetryChart.tsx              ← 02C
    ActionButtons.tsx               ← 02D
    IncidentTopBar.tsx              ← 02F
    ContextChips.tsx                ← 02G
    SourceStatusGrid.tsx            ← 02H
    KPIBar.tsx                      ← P5-03C
    analytics/
      VoiceQueryBox.tsx             ← 02E
      ConfirmationModal.tsx         ← 02E
      DriverReportCard.tsx          ← 02E
      ViolationsTable.tsx           ← 02E
      RouteTrackMap.tsx             ← 02E
      SpeedChart.tsx                ← 02E
      VideoSlidePanel.tsx           ← 02E
      FleetDriversList.tsx          ← 02E
      FleetVehiclesList.tsx         ← 02E
      FleetBarChart.tsx             ← 02E
      FleetMap.tsx                  ← 02E
      DriverMiniDashboard.tsx       ← 02E
      VehicleMiniDashboard.tsx      ← 02E
  screens/
    LiveMonitorScreen.tsx           ← P1-03E
    AnalyticsScreen.tsx             ← P2-03D
    UnifiedIncidentWindow.tsx       ← P3-03B
    EventFeedScreen.tsx             ← P4-03A
    TicketsScreen.tsx               ← 05B
data/mock/
  incidents.json                    ← 01C (обновить)
  vehicles.json                     ← 01D
  driver-report.json                ← 01F-A
  fleet-report.json                 ← 01F-B
  fleet-vehicles.json               ← 01F-B + 01F-D
hackathon/context/
  TECH-DESIGN.md                    ← 00a-A
```

---

Держи этот файл открытым весь день. Каждый час сверяйся с чекпоинтами.
