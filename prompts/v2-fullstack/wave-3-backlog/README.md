# Волна 3 · бэклог некритичных доработок

> **Не входит в P0/P1/P2-скоуп.** Накопленные неблокирующие правки и улучшения продукта,
> выявленные аудитами после Волн 1/2. Не блокируют релиз; выполняются **по мере готовности
> трека-владельца**, на его ветке `feat/*`, и сходятся на Барьере 3. Источник истины — `00-CONTRACT.md`.
> **Правило:** один промпт = один файл; промпт лежит в папке своего трека-владельца.

## Структура — по трекам (как Волна 1)

```text
wave-3-backlog/
├── track-b-backend/   🪟 Окно 1 · feat/backend — api/, data/
│   ├── w3-1 b13-ticket-sync           enum Status, deadline/is_overdue
│   ├── w3-2 diagnostic-source-data    source=DIAGNOSTIC, бейдж «⚙ Диагностика»
│   └── w3-5 no-video-incident         «нет видео» + «Запросить архив» (мёртвая ветка)
└── track-t-tests/     🪟 Окно 3 · feat/tests — api/tests, vitest
    ├── w3-3 backend-unit-coverage     unit b1–b13 (дозакрытие t1), гейт api≥85%
    └── w3-4 frontend-unit-coverage    unit d3–d5/f5–f13 (дозакрытие t3), гейт web≥80%
```

## Граф выполнения (как Волна 1)

```text
        ┌──────── после Барьера 2 (P1/P2 уже в main) ────────┐
        ▼                                                     ▼
  🪟 ОКНО 1 · backend (feat/backend)          🪟 ОКНО 3 · tests (feat/tests)
  track-b-backend/                            track-t-tests/
  w3-1 b13-ticket-sync     ┐                  w3-3 backend-unit-coverage  ┐ параллельно
  w3-2 diagnostic-source   ├ параллельно      w3-4 frontend-unit-coverage ┘
  w3-5 no-video-incident   ┘                       (зависимостей между пунктами нет)
        └──────────────────────────┬──────────────────────────┘
                                    ▼
                  🧪 БАРЬЕР 3 · barrier-3-hardening/x5-wave3-hardening
                  merge feat/backend+feat/tests → регресс (unit+API+фронт)
                  + гейт покрытия (api≥85% / web≥80%) → merge в main (ff-only)
```

## Как выполнять

В окне трека-владельца дай промпт (порядок между пунктами не важен, можно параллельно):

| 🪟 Окно | Промпты (∥) | Команда запуска |
| --- | --- | --- |
| 1 · backend | `w3-1` ∥ `w3-2` ∥ `w3-5` | `Выполни @prompts/v2-fullstack/wave-3-backlog/track-b-backend/w3-1-b13-ticket-sync.md` |
| 3 · tests | `w3-3` ∥ `w3-4` | `Выполни @prompts/v2-fullstack/wave-3-backlog/track-t-tests/w3-3-backend-unit-coverage.md` |

**Барьер 3** — в основном окне `skai_7` на ветке `integration`, после завершения пунктов:

```text
Выполни @prompts/v2-fullstack/barrier-3-hardening/x5-wave3-hardening.md
```

## Очередь — детали и приоритеты

| # | Промпт | Трек | Приоритет |
| --- | --- | --- | --- |
| W3-1 | [`track-b-backend/w3-1-b13-ticket-sync.md`](track-b-backend/w3-1-b13-ticket-sync.md) — синхронизация `b13` с contract-change #1 (enum `Status`, `deadline`/`is_overdue`) | b13 / backend | Средний |
| W3-2 | [`track-b-backend/w3-2-diagnostic-source-data.md`](track-b-backend/w3-2-diagnostic-source-data.md) — данные для `Source=DIAGNOSTIC` (бейдж «⚙ Диагностика», макет 07) | b1 / данные | Низкий |
| W3-5 | [`track-b-backend/w3-5-no-video-incident-reachable.md`](track-b-backend/w3-5-no-video-incident-reachable.md) — no-video инцидент достижим (мёртвая UI-ветка «нет видео» + `sensor_active_after_sec` §2); выявлено smoke x3 | b3 / данные (+T) | Средний |
| W3-3 | [`track-t-tests/w3-3-backend-unit-coverage.md`](track-t-tests/w3-3-backend-unit-coverage.md) — backend unit-покрытие `b1–b13` (дозакрытие t1), гейт `api/`≥85% | T / tests | Высокий |
| W3-4 | [`track-t-tests/w3-4-frontend-unit-coverage.md`](track-t-tests/w3-4-frontend-unit-coverage.md) — frontend unit-покрытие `d3–d5`/`f5–f13` (дозакрытие t3), гейт `web/src`≥80% | T / tests | Высокий |

## Куда складывать новые пункты

Новый backend/данные-пункт → `track-b-backend/wN-*.md`; тестовый → `track-t-tests/wN-*.md`
(+ строка в таблицу «Очередь» выше и в таблицу Волны 3 в `../EXECUTION.md`). Так бэклог остаётся executable.

> Закрытый аудитом дефект Волны 1 (b2 `_SPEED_LIMIT_TABLE` на legacy-кодах) исправлен в рамках
> Волны 1 (`feat/backend`, fix(b2)) и в бэклог Волны 3 не выносится.
