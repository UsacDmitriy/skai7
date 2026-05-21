# План выполнения — Team 7, 21 мая 2026

> **Инструмент:** Cherry Studio → OpenRouter (team key)
> **Бюджет:** $50 на команду · Реалистичный расход: $5–12
> **Правило:** один промпт = одна сессия · не параллельно

---

## Таблица весов файлов — знай перед запуском

| Файл | Токены | Стоимость input kimi | Действие |
|------|--------|---------------------|----------|
| `clade_design/*.html` | 425–478K | **$0.31–0.35** | ❌ НИКОГДА |
| `clade_design/*.png` (1.3MB+) | визуальные | ~$0.003 как image | Прикреплять как image |
| `verify-standalone.jpg` | ~3.5K | $0.003 | ✅ Дизайн-референс |
| `incidents.json` | ~12K | $0.009 | ⚠️ Только когда нужно |
| `types.ts` после генерации | ~1.3K | $0.001 | ✅ Всегда с кодом |
| `AGENTS.md` (целиком) | ~3K | $0.002 | ⚠️ Только нужные секции |
| `TECH-DESIGN.md` | ~2K | $0.001 | ✅ Для P0-экранов |

---

## Реалистичный бюджет

| Задача | Модель | Input токены | Output токены | Цена |
|--------|--------|-------------|---------------|------|
| 00a-A архитектура | kimi-k2.6 | ~5K + image | ~8K | ~$0.032 |
| 00a-B data contract | kimi-k2.6 | ~18K | ~6K | ~$0.034 |
| 00a-C design tokens | qwen:free | image | ~2K | $0 |
| Волны 01, 02, 04, 05 (~26 промптов) | qwen:free | ~3–8K каждый | ~5–10K | $0 |
| P0-экран 03B | kimi-k2.6 | ~10K | ~15K | ~$0.060 |
| P0-экран 03D | kimi-k2.6 | ~10K | ~15K | ~$0.060 |
| 10× итераций kimi (баги) | kimi-k2.6 | ~5K | ~5K | ~$0.040 |
| Резерв платный (DS V4 Flash) | v4-flash | — | — | ~$0.030 |
| Уже потрачено | — | — | — | ~$2.47 |
| **Итого** | | | | **~$2.75** |
| **Запас из $50** | | | | **~$47** |

> Если случайно прочитать один HTML-файл на kimi → +$0.35 за раз.
> 5 таких ошибок = +$1.75. Смотри таблицу весов перед каждой сессией.

---

## Модели в Cherry Studio

```
Добавить все до старта:
  qwen/qwen3-coder:free                    ← весь кодинг
  deepseek/deepseek-v4-flash:free          ← резерв при 429
  nvidia/nemotron-3-super-120b-a12b:free   ← контекст
  openai/gpt-oss-120b:free                 ← тексты
  poolside/laguna-xs.2:free                ← резерв
  moonshotai/kimi-k2.6                     ← архитектура + P0
  moonshotai/kimi-k2.6                     ← платный резерв
```

---

## 08:30–09:30 · Подготовка

| Время | Действие |
|-------|----------|
| 08:30 | git clone + npm install |
| 08:45 | Cherry Studio → team key → проверить kimi-k2.6 и qwen3-coder:free |
| 09:00 | Объявление тем |
| 09:10 | Получить datasets.zip → распаковать в корень репо |
| 09:15 | Открыть 3 CSV: selected_video_alarms.csv, track_points.csv, sensor_catalog.csv — записать заголовки |
| 09:20 | Прочитать AGENTS.md секции 1-2 + §4.5 (адаптация к данным) |

---

## 09:30–10:30 · Волна 00 + 00a · Контекст и архитектура

### 09:30 · Волна 00 — `nvidia/nemotron…:free`
```
Промпт:  prompts/hackathon/wave-00/00-read-context--nemotron.md
Читать:  AGENTS.md секции 1-2 (не весь файл)
Цена:    $0
```

### 09:45 · Волна 00a-A — Архитектура — `moonshotai/kimi-k2.6`
```
Промпт:  prompts/hackathon/wave-00a-architecture/00a-A-tech-design--kimi-k2.6.md
Читать:  AGENTS.md секции 1,3,5,6
Передать: РЕАЛЬНЫЕ заголовки CSV (из шага 09:15) + verify-standalone.jpg
❌ НЕ читать HTML-файлы из clade_design/
❌ НЕ использовать data/mock/*.json как референс полей
Цена:    ~$0.032
Итог:    hackathon/context/TECH-DESIGN.md (с реальными именами полей)
```

### 10:00 · Волна 00a-B — Data Contract — `moonshotai/kimi-k2.6`
```
Промпт:  prompts/hackathon/wave-00a-architecture/00a-B-data-contract--kimi-k2.6.md
Читать:  data/mock/driver-report.json + data/mock/incidents.json
         + раздел "Дерево компонентов" из TECH-DESIGN.md
Цена:    ~$0.034
Итог:    черновик src/types.ts
```

### 10:00 · Волна 00a-C — Design Tokens — `qwen/qwen3-coder:free`
```
Промпт:  prompts/hackathon/wave-00a-architecture/00a-C-design-tokens--qwen3.md
Image:   code/clade_design/Интерактивнй отчет/verify-standalone.jpg
❌ НЕ читать HTML
Цена:    $0
Итог:    черновик src/constants.ts
```

### 10:15 · Волна 00a-D — Сэмплы CSV — `qwen/qwen3-coder:free`
```
Промпт:  prompts/hackathon/wave-00a-architecture/00a-D-csv-samples--qwen3.md
Читать:  datasets/ready/video_events/selected_video_alarms.csv (первые 20 строк)
         + datasets/ready/navigation_problem_tracks/track_points.csv (первые 50 строк)
❌ НЕ читать весь CSV — только первые строки
Цена:    $0
Итог:    code/frontend/src/data/video_alarms_sample.json + track_points_sample.json
```

✅ **10:30 — Чекпоинт 0:** есть TECH-DESIGN.md + черновики types.ts и constants.ts

---

## 10:30–11:30 · Волна 1 · Foundation · `qwen/qwen3-coder:free`

Для каждого промпта передавать только то, что указано в таблице.

| # | Промпт | Доп. контекст | Итог |
|---|--------|---------------|------|
| 1 | 01A-types--qwen3.md | черновик types.ts из 00a-B | `src/types.ts` |
| 2 | 01B-constants--qwen3.md | черновик constants.ts из 00a-C | `src/constants.ts` |
| 3 | 01C-incidents-json--qwen3.md | — | `data/mock/incidents.json` |
| 4 | 01D-vehicles-json--qwen3.md | — | `data/mock/vehicles.json` |
| 5 | 01E-app-infra--qwen3.md | routing-секция из TECH-DESIGN.md | App.tsx + конфиги |
| 6 | 01F-A-driver-report--qwen3.md | — | `data/mock/driver-report.json` |
| 7 | 01F-B-fleet-reports--qwen3.md | — | `data/mock/fleet-report.json` |
| 8 | 01F-C-presets-types--qwen3.md | — | `src/analyticsPresets.ts` |
| 9 | 01F-D-fleet-vehicles--qwen3.md | — | `data/mock/fleet-vehicles.json` |

✅ **11:30 — Чекпоинт 1:** `npm run dev` → :5173, нет TypeScript ошибок

---

## 11:30–13:00 · Волна 2 · Компоненты · `qwen/qwen3-coder:free`

Передавать: промпт + только `src/types.ts` (не весь AGENTS.md).

| # | Промпт | Итог |
|---|--------|------|
| 9–15 | 02A–02H (по одному) | 7 компонентов Идеи #1 |
| 16–22 | 02E (каждый подраздел отдельно) | 7 компонентов Идеи #2 |

✅ **13:00 — Чекпоинт 2:** `ls src/components/*.tsx | wc -l` → 14+

---

## 13:00–13:30 · Обед

---

## 13:30–14:30 · Волна 3 · Экраны

### Простые → `qwen/qwen3-coder:free`
```
03A, 03E, 03C — передавать только src/types.ts
```

### P0-экраны → `moonshotai/kimi-k2.6` (~$0.06 каждый)
```
03B и 03D — передавать:
  - src/types.ts (~1.3K токенов)
  - hackathon/context/TECH-DESIGN.md (~2K токенов)
  ❌ НЕ передавать все компоненты целиком — только имена из TECH-DESIGN
```

✅ **14:30 — Чекпоинт 3:** `:5173/incident/inc-002` → видео слева + телематика справа

---

## 14:30–14:45 · Волна 4 · Роутинг · `qwen/qwen3-coder:free`

```
Промпт: 04-routing--qwen3.md
Контекст: текущий App.tsx + routing-секция из TECH-DESIGN.md
```

✅ **14:45 — Чекпоинт 4:** `/`, `/incident/inc-002`, `/analytics` работают

---

## 14:45–15:30 · Волна 5 · Полировка

| # | Промпт | Модель | Итог |
|---|--------|--------|------|
| 05A | tickets-table | qwen:free | TicketsTable.tsx |
| 05B | tickets-screen | qwen:free | TicketsScreen.tsx |
| 05C | smoke-checklist | nemotron:free | чеклист текстом |
| 05D | demo-script | gpt-oss:free | hackathon/PITCH.md |

✅ **15:30 — Чекпоинт 5:** оба Flow работают end-to-end

---

## 15:30–16:00 · Буфер

```
Ошибка TS:      → qwen:free «Исправь. Только этот файл: [код]»
npm build fails → первые 30 строк ошибок → qwen:free
Сложный баг P0: → kimi-k2.6, только проблемный файл (~$0.04)
Rate limit all: → deepseek/deepseek-v4-flash ($0.001/req)
```

---

## 16:00–18:00 · Заморозка → Презентация

| Время | Действие |
|-------|----------|
| 16:30 | Записать резервное видео |
| 16:30 | Первая репетиция по PITCH.md |
| 17:30 | Вторая репетиция, 4 минуты |
| 18:00 | Выступление |
