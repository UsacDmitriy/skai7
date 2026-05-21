# Wave 03 — Экраны

## Порядок запуска (по убыванию приоритета)

| Файл | Экран | Модель | Порядок |
|------|-------|--------|---------|
| `P1-03E-live-monitor--kimi-k2.6.md` | Живой мониторинг (главный) | kimi-k2.6 | #1 |
| `P2-03D-analytics-screen--kimi-k2.6.md` | Интерактивный отчёт | kimi-k2.6 | #2 |
| `P3-03B-incident-card--kimi-k2.6.md` | Карточка инцидента | kimi-k2.6 | #3 |
| `P4-03A-events-feed--qwen3.md` | Лента событий | qwen3:free | #4 |
| `P5-03C-kpi-bar--qwen3.md` | KPI-бар | qwen3:free | #5 |

## Зависимости

- `03E` зависит от: wave-01-foundation
- `03D` зависит от: `02E-idea2-analytics-components`, `01F-A-driver-report`, `01F-B-fleet-reports`
- `03B` зависит от: `02A-idea1-IncidentCard`, `02B-idea1-VideoPanel`, `02C-idea1-TelemetryChart`
- `03A` зависит от: `01C-incidents-json`
- Все зависят от: `wave-01-foundation` (types.ts, constants.ts)

## Запуск

P1-P3 на kimi-k2.6 последовательно. P4-P5 на qwen3:free параллельно с P1-P3.
