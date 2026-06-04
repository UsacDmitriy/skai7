# x4 · Сквозной smoke P1/P2 + Voice/NLU (финал расширения)

> **Барьер 2 — финал Волны 2 (расширение).** **Владеет:** только запуск/проверки (smoke). Авторство тестов —
> Codex-задачи `prompts/codex-tasks/T2-api-integration-tests` (`test_reports_api`, `test_p1p2_api`) и `T3`.
> Ничего не переписывает — при провале заводит дефект соответствующему треку (b7–b13 / d4,d5 / f5–f13).
> Запускается после Барьера 1 (x1–x3, роутеры включены) и завершения Волны 2 (расширение P1/P2).

## Перед стартом — склейка волны 2 (main держим стабильным)

В окне `skai_7` на ветке `integration`. **`main` сейчас = стабильный P0 (после x3) — не трогаем**, пока P1/P2-smoke не зелёный.

```bash
cd /Users/dimausac/projects/skai_7
git checkout integration
git merge feat/backend feat/web   # волна 2: b7–b13, d4/d5, f5–f13
```

Если в волне 2 менялись роутеры/прокси — **перезапусти x2** (авто-обход подхватит новые роутеры b11–b13). Конфликты разруливаем на `integration`.

## Проверка предыдущего шага (x3 · P0 e2e зелёный)

Не валидируй P1/P2 поверх сломанного P0:

- P0-smoke из x3 всё ещё проходит (incidents end-to-end, обогащение не NULL).
- `main` указывает на P0-стабильный коммит (`git log main -1 --oneline`).
- Слияние волны 2 прошло без конфликтов (`git status` чисто).

Не прошло — **стоп**, дефект, чиним на `integration`.

## Цель

Подтвердить, что расширение (идеи #2 полностью, #4–#10) работает end-to-end: реальные отчёты/voice/NLU,
лента, карта, заявки, алерт, видеодосье, РЭБ, саботаж, роли — на живом API и на фронте.

## Данные/бэкенд

1. `make db` → дополнительно к x3: таблицы `driver_reference`>0 и `driver_trips`>0; views
   `v_driver_report`, `v_fleet`, `v_vehicle`, `v_sabotage`, `v_reb` существуют (`SELECT ... LIMIT 1` без ошибок).
2. `make api`, проверить **регистрацию всех роутеров** (`GET /docs` показывает теги
   incidents/reports/vehicles/actions/tickets/alerts/trips/sabotage/reb) и эндпоинты:
   - `GET /api/reports/driver/{plate}` → 200 `DriverReport`: `kpi` (всего/ВА/телематика/грубых),
     `disciplinary_warning`, `violations[]` с `is_gross`, водитель из `driver_reference`.
   - `GET /api/reports/fleet?view=drivers` и `?view=vehicles` → 200 `FleetReport` (оба разреза);
     `by_vehicles[]` несёт `risk_score`, `gross`, `cameras_ok="N/3"`.
   - `GET /api/reports/vehicle/{plate}` → 200 `VehicleReport`: `cameras` длины 3, `drivers` ≥1
     (роль main/secondary из `driver_trips`).
   - `POST /api/reports/query` `{ "text": "Нарушения Иванова за 3 дня" }` → 200 `{query, report}`;
     `query.kind="driver"`. `"отчёт по парку"` → `kind="fleet"`. (Без `GROQ_API_KEY` — fallback regex.)
   - `POST /api/reports/transcribe` (wav multipart) → 200 `{text, lang, confidence}` (faster-whisper).
   - `GET /api/tickets` → 200 `Ticket[]` (из `output/actions.csv`).
   - `GET /api/alerts/{id}` → 200 `DispatchAlert` (`video_window_sec=15`).
   - `GET /api/trips/{id}` → 200 `TripDossier` (track + timeline).
   - `GET /api/reb/{id}` → 200 `RebRecovery` (`gap_periods[]` из `navigation`).
   - `GET /api/sabotage` → 200 `SabotageEvent[]` (`dms_dark=true` + `speed_kmh>0`).

## pytest (`api/tests/`)

- `test_reports.py` — driver/fleet/vehicle отчёты, gross-правило (`severity=critical OR code∈{OVERSPEED,DMS_SMOKING}`),
  `disciplinary_warning` (gross≥3 / safety_score<60), NLU-fallback парсит ФИО/госномер/период.
- `test_p1p2.py` — `TestClient` на tickets/alerts/trips/reb/sabotage (коды/схемы).

## Фронт

3. `make web`, проверить экраны на живом API и фикстурах (`VITE_USE_FIXTURES=true`):
   - `/` лента: badge источника, фильтр «Нет видео», ролевой switcher, поиск, клик→карточка.
   - `/monitor`: **карта-герой**, 1 `unit_id`=1 маркер (дедуп), цвет по severity, тёмная тема, роль «Логист» скрывает DMS.
   - `/report`: 🎤→`transcribe`→текст→`query`→`ConfirmationModal`→дашборд В-1/В-2 (toggle По водителям/По ТС);
     клик по нарушению → видео справа (DMS→ch5, ADAS→ch1); KPI-плашки и `disciplinary_warning` видны.
   - `/tickets`, `/alert/:id`, `/trip/:id`, `/reb/:id`, виджет саботажа — открываются на данных.
4. `cd web && npm run typecheck` — без ошибок (типы §3.1 + §7.5).

## Критерии приёмки

- Все P1/P2-эндпоинты и экраны проходят end-to-end; роутеры b11–b13 зарегистрированы (видны в `/docs`).
- Реальный голос→NLU→отчёт работает (faster-whisper + Groq/fallback); грубые/взыскание считаются по §7.5.
- Карта-монитор — карта доминирует, дедупликация 1 ТС=1 маркер; ролевой режим фильтрует слои.
- Sync «видео ↔ маркер телеметрии» (П5) работает в карточке (см. x3 + §6).

## Финализация — продвинуть main (полный P1/P2 стабилен)

**Только если все критерии приёмки выше зелёные**, зафиксируй полный продукт в `main`:

```bash
git -C /Users/dimausac/projects/skai_7 checkout main
git merge --ff-only integration       # main догоняет integration (fast-forward)
git checkout integration
```

Smoke красный → **`main` остаётся на P0** (из x3), заводим дефект трека и чиним на `integration`. `main` всегда = последний зелёный релиз.
