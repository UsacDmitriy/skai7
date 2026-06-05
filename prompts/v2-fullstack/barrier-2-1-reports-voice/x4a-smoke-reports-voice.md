# x4a · Барьер 2.1 — smoke среза Reports & Voice

> **Промежуточный барьер Волны 2.1.** **Владеет:** только запуск/проверки (smoke). Авторство —
> **Модель:** 🔴 Opus — высокие ставки: интеграция / синк / алгоритм / анти-регресс / killer-feature / барьер.
> треки B (`b7`,`b8`,`b9`,`b10`) и F (`d5`,`f7`). Ничего не переписывает — при провале заводит дефект
> треку. Запускается после Барьера 1 (x1–x3 зелёные) и завершения Волны 2.1. **`main` не трогает** —
> это checkpoint на `integration`; `main` продвигается только финальным Барьером 2 (x4).

## Перед стартом — склейка Волны 2.1

В окне `skai_7` на ветке `integration`. **`main` = стабильный P0 (после x3) — не трогаем.**

```bash
cd /Users/dimausac/projects/skai_7
git checkout integration

# GUARD: merge берёт только коммиты — стоп, если в worktree есть незакоммиченные изменения.
for w in backend web tests; do
  d=".worktrees/$w"; [ -d "$d" ] || continue
  test -z "$(git -C "$d" status --porcelain)" || { echo "❌ $w: незакоммичено — закоммить в worktree и повтори барьер"; exit 1; }
done

git merge feat/backend feat/web   # 2.1: b7,b8,b9,b10 ; d5,f7
```

Если менялись роутеры/прокси — **перезапусти x2** (подхватит новые роутеры). Конфликты — на `integration`.

## Проверка предыдущего шага (x3 · P0 e2e зелёный)

- P0-smoke из x3 всё ещё проходит (incidents end-to-end, обогащение не NULL).
- Слияние 2.1 прошло без конфликтов (`git status` чисто).

Не прошло — **стоп**, дефект, чиним на `integration`.

## Цель

Подтвердить срез «отчёты + голос» (идеи #2/#4) на живом API и фронте: справочник водителей,
отчёты В-1/В-2, транскрипция + NLU → отчёт.

## Данные/бэкенд

1. `make db` → `driver_reference`>0 и `driver_trips`>0; views `v_driver_report`, `v_fleet`, `v_vehicle`
   существуют (`SELECT ... LIMIT 1` без ошибок).
2. `make api`, проверить эндпоинты:
   - `GET /api/reports/driver/{plate}` → 200 `DriverReport` (`kpi`, `disciplinary_warning`, `violations[]` с `is_gross`).
   - `GET /api/reports/fleet?view=drivers` и `?view=vehicles` → 200 `FleetReport` (оба разреза).
   - `GET /api/reports/vehicle/{plate}` → 200 `VehicleReport` (`cameras` длины 3).
   - `POST /api/reports/query` `{ "text": "Нарушения Иванова за 3 дня" }` → 200 `{query,report}`, `query.kind="driver"`;
     `"отчёт по парку"` → `kind="fleet"` (без `GROQ_API_KEY` — fallback regex).
   - `POST /api/reports/transcribe` (wav multipart) → 200 `{text, lang, confidence}` (faster-whisper).

## Фронт

3. `make web`, экран «Аналитика/Voice» (`f7`) на живом API и фикстурах (`VITE_USE_FIXTURES=true`):
   🎤 → `transcribe` → текст → `query` → `ConfirmationModal` → дашборд В-1/В-2 (toggle По водителям/По ТС);
   клик по нарушению → видео справа (DMS→ch5, ADAS→ch1); KPI и `disciplinary_warning` видны.
4. `cd web && npm run typecheck` — без ошибок.

## Критерии приёмки

- Все reports/voice-эндпоинты отвечают; голос→NLU→отчёт работает (faster-whisper + Groq/fallback).
- Грубые/взыскание считаются по §7.5; экран `f7` проходит флоу end-to-end.

## Финализация

`main` **не двигаем**. Зелёно → переходим к Волне 2.2. Красно → дефект трека, чиним на `integration`,
к 2.2 не переходим.
