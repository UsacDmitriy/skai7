# x4b · Барьер 2.2 — smoke прикладных экранов

> **Промежуточный барьер Волны 2.2.** **Владеет:** только запуск/проверки (smoke). Авторство —
> **Исполнение:** owner-only gate — Claude/Codex; ClinePass excluded from shared contracts, integration, deterministic acceptance, and commit — высокие ставки: интеграция / синк / алгоритм / анти-регресс / killer-feature / барьер.
> треки B (`b11`,`b12`,`b13`) и F (`d4`,`f5`,`f6`,`f8`–`f13`). Ничего не переписывает — при провале
> заводит дефект треку. Запускается после Барьера 2.1 (x4a зелёный) и завершения Волны 2.2.
> **`main` не трогает** — checkpoint на `integration`.

## Перед стартом — склейка Волны 2.2

```bash
cd /Users/dimausac/projects/skai_7
git checkout integration

# GUARD: merge берёт только коммиты — стоп, если в worktree есть незакоммиченные изменения.
for w in backend web tests; do
  d=".worktrees/$w"; [ -d "$d" ] || continue
  test -z "$(git -C "$d" status --porcelain)" || { echo "❌ $w: незакоммичено — закоммить в worktree и повтори барьер"; exit 1; }
done

git merge feat/backend feat/web   # 2.2: b11,b12,b13 ; d4,f5,f6,f8–f13
```

⚠ **Обязательно перезапусти x2** — b11/b13 добавили роутеры в `ALL_ROUTERS`; без rewire `/api/sabotage`,
`/api/reb`, `/api/tickets`, `/api/alerts`, `/api/trips` отдадут 404.

## Проверка предыдущего шага (x4a · Reports/Voice зелёный)

- smoke 2.1 (отчёты/voice) всё ещё проходит.
- Слияние 2.2 прошло без конфликтов (`git status` чисто).

Не прошло — **стоп**, дефект, чиним на `integration`.

## Цель

Подтвердить прикладные экраны (идеи #5–#10): заявки, диспетчерский алерт, видеодосье, РЭБ,
саботаж, карта-монитор, ролевые режимы — на живом API и фронте.

## Данные/бэкенд

1. `make db` → views `v_sabotage`, `v_reb` существуют.
2. `make api`, **регистрация роутеров** (`GET /docs` показывает теги tickets/alerts/trips/sabotage/reb):
   - `GET /api/tickets` → 200 `Ticket[]` (из `output/actions.csv`).
   - `GET /api/alerts/{id}` → 200 `DispatchAlert` (`video_window_sec=15`).
   - `GET /api/trips/{id}` → 200 `TripDossier` (track + timeline).
   - `GET /api/reb/{id}` → 200 `RebRecovery` (`gap_periods[]`).
   - `GET /api/sabotage` → 200 `SabotageEvent[]` (`dms_dark=true` + `speed_kmh>0`).

## Фронт

3. `make web`, экраны на живом API и фикстурах (`VITE_USE_FIXTURES=true`):
   - `/` лента (`f5`): badge источника, фильтр «Нет видео», поиск, клик→карточка.
   - `/monitor` (`f6`+`d4`): **карта-герой**, 1 `unit_id`=1 маркер (дедуп), цвет по severity, роль «Логист» скрывает DMS.
   - `/tickets` (`f8`), `/alert/:id` (`f9`), `/trip/:id` (`f10`), `/reb/:id` (`f11`), виджет саботажа (`f12`) — открываются на данных.
   - ролевой switcher (`f13`) согласованно фильтрует слои/колонки во всех экранах.
4. `cd web && npm run typecheck` — без ошибок.

## Критерии приёмки

- Роутеры b11–b13 зарегистрированы (видны в `/docs`), все прикладные эндпоинты отвечают.
- Карта-монитор доминирует, дедуп 1 ТС=1 маркер; ролевой режим фильтрует слои.
- Все экраны `f5/f6/f8–f13` открываются end-to-end.

## Финализация

`main` **не двигаем**. Зелёно → переходим к Волне 2.3 (тесты). Красно → дефект трека, чиним на `integration`.
