# План выполнения

> **Правило:** один промпт = одна сессия · не параллельно

---

## Подготовка

- `git clone` + установка зависимостей
- Получить набор данных → распаковать в корень репозитория
- Открыть 3 CSV: `selected_video_alarms.csv`, `track_points.csv`, `sensor_catalog.csv` — записать заголовки
- Прочитать `AGENTS.md` секции 1-2 + §4.5 (адаптация к данным)

---

## Волна 00 + 00a · Контекст и архитектура

### Волна 00 — чтение контекста
```
Промпт:  prompts/waves/wave-00/00-read-context.md
Читать:  AGENTS.md секции 1-2 (не весь файл)
```

### Волна 00a-A — Архитектура
```
Промпт:  prompts/waves/wave-00a-architecture/00a-A-tech-design.md
Читать:  AGENTS.md секции 1,3,5,6
Передать: РЕАЛЬНЫЕ заголовки CSV (из шага подготовки) + verify-standalone.jpg
❌ НЕ читать HTML-файлы из clade_design/
❌ НЕ использовать data/mock/*.json как референс полей
Итог:    init/context/TECH-DESIGN.md (с реальными именами полей)
```

### Волна 00a-B — Data Contract
```
Промпт:  prompts/waves/wave-00a-architecture/00a-B-data-contract.md
Читать:  data/mock/driver-report.json + data/mock/incidents.json
         + раздел "Дерево компонентов" из TECH-DESIGN.md
Итог:    черновик src/types.ts
```

### Волна 00a-C — Design Tokens
```
Промпт:  prompts/waves/wave-00a-architecture/00a-C-design-tokens.md
Image:   code/clade_design/Интерактивнй отчет/verify-standalone.jpg
❌ НЕ читать HTML
Итог:    черновик src/constants.ts
```

### Волна 00a-D — Сэмплы CSV
```
Промпт:  prompts/waves/wave-00a-architecture/00a-D-csv-samples.md
Читать:  datasets/ready/video_events/selected_video_alarms.csv (первые 20 строк)
         + datasets/ready/navigation_problem_tracks/track_points.csv (первые 50 строк)
❌ НЕ читать весь CSV — только первые строки
Итог:    code/frontend/src/data/video_alarms_sample.json + track_points_sample.json
```

✅ **Чекпоинт 0:** есть TECH-DESIGN.md + черновики types.ts и constants.ts

---

## Волна 1 · Foundation

Для каждого промпта передавать только то, что указано в таблице.

| # | Промпт | Доп. контекст | Итог |
|---|--------|---------------|------|
| 1 | 01A-types.md | черновик types.ts из 00a-B | `src/types.ts` |
| 2 | 01B-constants.md | черновик constants.ts из 00a-C | `src/constants.ts` |
| 3 | 01C-incidents-json.md | — | `data/mock/incidents.json` |
| 4 | 01D-vehicles-json.md | — | `data/mock/vehicles.json` |
| 5 | 01E-app-infra.md | routing-секция из TECH-DESIGN.md | App.tsx + конфиги |
| 6 | 01F-A-driver-report.md | — | `data/mock/driver-report.json` |
| 7 | 01F-B-fleet-reports.md | — | `data/mock/fleet-report.json` |
| 8 | 01F-C-presets-types.md | — | `src/analyticsPresets.ts` |
| 9 | 01F-D-fleet-vehicles.md | — | `data/mock/fleet-vehicles.json` |

✅ **Чекпоинт 1:** `npm run dev` → :5173, нет TypeScript ошибок

---

## Волна 2 · Компоненты

Передавать: промпт + только `src/types.ts` (не весь AGENTS.md).

| # | Промпт | Итог |
|---|--------|------|
| 9–15 | 02A–02H (по одному) | 7 компонентов Идеи #1 |
| 16–22 | 02E (каждый подраздел отдельно) | 7 компонентов Идеи #2 |

✅ **Чекпоинт 2:** `ls src/components/*.tsx | wc -l` → 14+

---

## Волна 3 · Экраны

### Простые экраны
```
03A, 03E, 03C — передавать только src/types.ts
```

### P0-экраны
```
03B и 03D — передавать:
  - src/types.ts
  - init/context/TECH-DESIGN.md
  ❌ НЕ передавать все компоненты целиком — только имена из TECH-DESIGN
```

✅ **Чекпоинт 3:** `:5173/incident/inc-002` → видео слева + телематика справа

---

## Волна 4 · Роутинг

```
Промпт: 04-routing.md
Контекст: текущий App.tsx + routing-секция из TECH-DESIGN.md
```

✅ **Чекпоинт 4:** `/`, `/incident/inc-002`, `/analytics` работают

---

## Волна 5 · Полировка

| # | Промпт | Итог |
|---|--------|------|
| 05A | tickets-table | TicketsTable.tsx |
| 05B | tickets-screen | TicketsScreen.tsx |
| 05C | smoke-checklist | чеклист текстом |
| 05D | demo-script | init/PITCH.md |

✅ **Чекпоинт 5:** оба Flow работают end-to-end

---

## Буфер · Исправление ошибок

```
Ошибка TS:      → «Исправь. Только этот файл: [код]»
npm build fails → первые 30 строк ошибок
Сложный баг P0: → только проблемный файл
```

---

## Демо

Демо по `05D-demo-script.md`:

- **Flow 1:** inc-002 → видео + телеметрия + [Создать заявку]
- **Flow 2:** inc-003 → нет видео → [Запросить архив]
- **Flow 3:** голос «Нарушения Иванова за 3 дня» → подтверждение → отчёт
