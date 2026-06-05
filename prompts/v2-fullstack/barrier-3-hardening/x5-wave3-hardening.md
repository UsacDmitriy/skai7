# x5 · Барьер 3 — хардненинг Волны 3 (полный регресс + гейт покрытия)

> **Барьер 3 — финал Волны 3 (бэклог + тест-хардненинг).** **Владеет:** только запуск/проверки (regress + coverage).
> Авторство тестов — Track T (`wave-3-backlog/w3-3-backend-unit-coverage`, `w3-4-frontend-unit-coverage`);
> доработки — `w3-1` (b13/Ticket), `w3-2` (DIAGNOSTIC). Ничего не переписывает — при провале заводит
> дефект треку-владельцу. Запускается **после Барьера 2 (x4 зелёный, P1/P2 в `main`)** и завершения Волны 3.

## Перед стартом — склейка Волны 3 (main держим стабильным)

В окне `skai_7` на ветке `integration`. **`main` сейчас = стабильный P1/P2 (после x4) — не трогаем**,
пока полный регресс Волны 3 не зелёный.

```bash
cd /Users/dimausac/projects/skai_7
git checkout integration
git merge feat/backend feat/web feat/tests   # волна 3: w3-1..w3-4
```

Конфликты разруливаем на `integration`.

## Проверка предыдущего шага (x4 · P1/P2 зелёный)

Не валидируй хардненинг поверх сломанного релиза:

- P1/P2-smoke из x4 всё ещё проходит; `main` указывает на P1/P2-стабильный коммит (`git log main -1 --oneline`).
- Слияние Волны 3 прошло без конфликтов (`git status` чисто).

Не прошло — **стоп**, дефект, чиним на `integration`.

## Цель

Подтвердить, что бэклог-доработки применены и **всё решение покрыто unit-тестами по промптам**,
а полный регресс (unit + API + фронт) зелёный с заданным порогом покрытия.

## Доработки бэклога (w3-1 / w3-2)

1. `grep -n '"new"' prompts/v2-fullstack/wave-2-2-applied/track-b-backend/b13-tickets-alerts-trips.md` → **пусто** (W3-1: enum `Status` без `new`).
   Если `tickets_service` реализован — `Ticket.status` дефолт `"active"`, есть `deadline`/`is_overdue`.
2. W3-2: либо `grep -n DIAGNOSTIC data/analysis/alarm_types.json` непуст (есть строка `source:"DIAGNOSTIC"`),
   либо в `00-CONTRACT.md` рядом с changelog #1(a) зафиксировано, что значение зарезервировано без данных.

## Регресс + гейт покрытия

**Backend (w3-3 + t1):**

```bash
make db
pytest api/tests -q                       # unit + integration — зелёный
pytest --cov=api api/tests/unit           # покрытие api/ ≥ 85%, enrichment.py ≥ 90%
```

**Frontend (w3-4 + t3):**

```bash
cd web && npm ci
npx vitest run --coverage                 # зелёный; покрытие web/src ≥ 80%
npm run typecheck                         # без ошибок (типы §3.1+§7.5)
```

## Критерии приёмки

- Полный регресс зелёный: `pytest api/tests` + `npx vitest run` без падений.
- Покрытие достигает порогов: `api/` ≥ 85% (enrichment ≥ 90%), `web/src` ≥ 80%.
- Все модули по промптам имеют unit-файл (b1–b13 в `api/tests/unit/**`; d3–d5/f5–f13 в `web/src/**/*.test.tsx`).
- W3-1/W3-2 отражены (проверки выше зелёные).

## Финализация — продвинуть main (Волна 3 стабильна)

**Только если все критерии приёмки выше зелёные:**

```bash
git -C /Users/dimausac/projects/skai_7 checkout main
git merge --ff-only integration       # main догоняет integration (fast-forward)
# если ff-only падает (в main снова попали прямые коммиты) →
#   git merge --no-ff integration -m "merge integration → main (Волна 3 hardening)"
git checkout integration
```

Регресс/покрытие красные → **`main` остаётся на P1/P2** (из x4), заводим дефект трека и чиним на `integration`.
`main` всегда = последний зелёный релиз.
