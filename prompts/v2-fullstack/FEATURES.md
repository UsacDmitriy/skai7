# FEATURES — матрица трассировки фич (идеи #1–#10)

> **Зачем.** Волны делятся по приоритету (P0/P1/P2) и треку (backend ∥ web ∥ tests), а граница —
> контракт. При такой модели одна фича **размазана** по нескольким промптам и собирается только
> на барьере. Эта матрица гарантирует, что **каждая фича проработана сквозь весь стек** —
> data → backend → API → web → tests → приёмка — и ничто не недоспецифицировано.
>
> Источник истины полей/схем/эндпоинтов — `00-CONTRACT.md`. Здесь — **трассировка и Definition of Done**,
> а не дубль контракта. Любая новая фича → строка в мастер-таблице + блок DoD ниже.
>
> **Кто читает.** Этот файл — для **ведущего/планировщика** (карта «фича → её промпты», полнота скоупа)
> и **оператора барьера** (per-feature приёмка). Исполнитель отдельного промпта его не открывает —
> поэтому **сама глубина (edge-cases, негативы, состояния) впечатана в секцию `## Check` каждого
> фич-промпта** (`b7`–`b14`, `f5`–`f14`, `d4`/`d5`). Матрица и DoD — чтобы держать это в синхроне.
> P0-фичи #1/#3 (`b2`/`f4`) уже выполнены в Волне 1 → их DoD-доработка вынесена в `b14`/`f14` (Волна 2.1).

## Единый Definition of Done (для любой фичи)

Фича считается «максимально проработанной», только если **все** пункты закрыты:

1. **Контракт** — схема (§3.1/§7.5) и эндпоинт (§3.x/§7.4) зафиксированы; UI-состояния описаны (§7.8).
2. **Данные** — таблица/view в DuckDB существует и непуста **или** явно покрыт пустой кейс (не падать).
3. **Backend** — сервис + роутер; **негативные кейсы** (404 / пустой список / нет файла) детерминированы.
4. **Frontend** — экран на живом API **и** фикстурах (`VITE_USE_FIXTURES=true`); состояния
   **loading / empty / error**; ролевой режим; a11y (фокус, клавиатура, роли); локали дат/таймзоны.
5. **Edge cases** — пустые данные, отсутствие видео, неизвестный `id`, оффлайн-камера — обработаны.
6. **Tests** — unit (логика) + API (коды/схемы) + front (рендер/взаимодействие): **happy + негатив**.
7. **Приёмка** — проходит smoke своего барьера (см. колонку «Приёмка»); типы (`npm run typecheck`) зелёные.

> Per-feature глубина unit-покрытия дозакрывается в Волне 3 (`w3-3`/`w3-4`), но базовый happy+негатив —
> уже в `tu-*`/t2/t3 (Волна 2.3; backend-unit вынесен в per-feature `tu-*`). DoD не считается закрытым без негативных кейсов.

## Мастер-таблица трассировки

| # | Фича | Данные / схема (§) | Backend | Web (+design) | Tests | Волна | Приёмка |
|---|---|---|---|---|---|---|---|
| #1 | Синк видео↔маркер телеметрии | `track_points`, `TelemetryPoint` §3.1, §6 | b3, b5 (`get_telemetry`) | f4 IncidentCard **+ f14 (хардненинг)** ; d2/d3 | t3 (sync) | 1 (P0) + 2.1 (f14) | x3 / x4 |
| #3 | Обогащение / risk-score | `alarm_type_catalog`, enrichment §2 | b1, b2 **+ b14 (хардненинг)** | f4 (badge/score) ; d2 | tu-enrichment | 1 (P0) + 2.1 (b14) | x3 / x4 |
| #2 | Voice/NLU + отчёты В-1/В-2 | `driver_reference` §7.1, `v_driver_report`/`v_fleet`/`v_vehicle`, `DriverReport`/`FleetReport`/`VehicleReport` §7.5 | b7→b10, b8 (stt), b9 (nlu) | d5 voice-timeline → f7 analytics-voice | tu-driver/nlu/reports, t2, t3 | 2.1 | x4a |
| #4 | Лента событий (`/`) | `v_incidents`, `IncidentRow` §3.1 | b3, b6 | f5 events-feed ; d3 | t3 | 2.2 | x4b |
| #4/#10 | Монитор-карта (`/monitor`) | `v_incidents`, `unit_id`/`lat/lon` | b6 | d4 map-primitives → f6 monitor-map | t3 (дедуп) | 2.2 | x4b |
| #5 | Dispatch alert (`/alert/:id`) | `DispatchAlert` §7.5 (`auto_request_video`, видео ±15с) | b13 (alerts) | f9 dispatch-alert | t2/t3 | 2.2 | x4b |
| #6 | Заявки (`/tickets`) | `output/actions.csv`, `Ticket` §7.5 (`deadline`/`is_overdue`) | b13 (tickets) | f8 tickets | t2/t3 | 2.2 | x4b |
| #7 | Видеодосье (`/trip/:id`) | `track_points`, `TripDossier` §7.5 (track + timeline) | b13 (trips) | f10 trip-dossier | t2/t3 | 2.2 | x4b |
| #8 | РЭБ-восстановление (`/reb/:id`) | `navigation__track_periods`, `v_reb`, `RebRecovery` §7.5 | b12 reb | f11 reb-recovery | tu-reb, t2, t3 | 2.2 | x4b |
| #9 | Детекция саботажа | `v_sabotage` (тёмный DMS + speed>0), `SabotageEvent` §7.5 | b11 sabotage | f12 sabotage | tu-sabotage, t2, t3 | 2.2 | x4b |
| #10 | Карта по ролям | `v_vehicle` (1 ТС=N водителей), ролевые слои | b10 (v_vehicle) | f6 monitor-map + f13 role-toggle | t3 (роли) | 2.2 | x4b |

> Бэклог/хардненинг, относящийся к фичам: W3-1 (Ticket §7.5 для #6), W3-2 (DIAGNOSTIC для #9-смежного),
> W3-5 (мёртвая ветка «нет видео» для #1/#4) — см. `wave-3-backlog/`.

## Per-feature Definition of Done

Ниже — что именно делает каждую фичу «проработанной до максимума» (поверх единого DoD).
Полные контуры полей — в `00-CONTRACT.md`; здесь — фокус на глубине и edge-кейсах.

### #1 · Синк видео↔маркер телеметрии (P0, x3; доработка — `f14`, Волна 2.1)
- **Depth:** при `onTimeUpdate` плеера маркер на `TelemetryChart` движется к точке за `currentTime`; клик по графику перематывает видео (§6).
- **Edge:** нет видео → плеер показывает placeholder, график живёт автономно; пустой `track` → «нет телеметрии», не падать.
- **Реализация глубины:** базовый экран — `f4` (выполнен, Волна 1); состояния/sync/a11y/локали — `wave-2-1-reports-voice/track-f-frontend/f14-incidentcard-hardening`.
- **Tests:** `playheadOffset` обновляется на `onTimeUpdate`; seek по графику → `seekTo`.

### #3 · Обогащение / risk-score (P0, x3; доработка — `b14`, Волна 2.1)
- **Depth:** `risk_score∈[0,100]`, монотонность по severity; `is_night`, `ax`, `speed_limit_for`, `confidence` детерминированы.
- **Edge:** неизвестный `alarm_code` → дефолтный label/severity, без NULL; нет видео → `confidence −10`.
- **Реализация глубины:** базовый модуль — `b2` (выполнен, Волна 1); клампы/дефолты/детерминизм — `wave-2-1-reports-voice/track-b-backend/b14-enrichment-hardening`.
- **Tests:** `tu-enrichment` → `test_enrichment` (Волна 2.3) + `w3-3` углубление (Волна 3).

### #2 · Voice/NLU + отчёты (2.1, x4a)
- **Depth:** `transcribe` (faster-whisper) → `query` (Groq/regex-fallback) → В-1/В-2 дашборд; gross-правило и `disciplinary_warning` по §7.5.
- **Edge:** без `GROQ_API_KEY` → regex-fallback; битый/пустой wav → graceful; мусор-запрос → безопасный дефолт `kind`.
- **Tests:** `tu-reports`/`tu-nlu`/`tu-driver` (правила/fallback/сиды), t2 (`test_reports_api`), t3 (`f7` флоу).

### #4 · Лента + Монитор (2.2, x4b)
- **Depth:** badge источника `[📹/⚡/⚡📹]`, фильтр «Нет видео», поиск по plate/ФИО, ролевой switcher; на карте 1 `unit_id`=1 маркер, цвет по severity, тёмная тема.
- **Edge:** пустой список → empty-state; роль «Логист» → без DMS-алармов; дубли алармов одного ТС → один маркер.
- **Tests:** t3 фильтры/поиск + дедуп монитора.

### #5 · Dispatch alert (2.2, x4b)
- **Depth:** при `auto_request_video=true` — модал с видео ±15с + 3 кнопки действия; телеметрия момента.
- **Edge:** неизвестный `id` → 404 (роутер) / экран «не найдено»; нет видео-окна → плашка.
- **Tests:** t2 (`/api/alerts/{id}` коды/схема), t3 (модал).

### #6 · Заявки (2.2, x4b)
- **Depth:** таблица из `output/actions.csv`; фильтры тип/статус/дата; enum `Status` отображается; **оверлей «⏱ Просрочено» по `is_overdue`, не по статусу**.
- **Edge:** нет CSV → `[]` и empty-state (не ошибка); `deadline=null` → `is_overdue=false`.
- **Tests:** t2 (`/api/tickets`), t3 (`f8` оверлей просрочки), w3-1 синхронизация схемы.

### #7 · Видеодосье (2.2, x4b)
- **Depth:** `TripDossier{vehicle_plate, track, timeline}`; клик по точке таймлайна → видео момента; `has_video` управляет иконкой.
- **Edge:** нет данных по `id` → 404; точки без видео → иконка-заглушка.
- **Tests:** t2 (`/api/trips/{id}`), t3 (таймлайн).

### #8 · РЭБ-восстановление (2.2, x4b)
- **Depth:** `gap_periods[]` из `navigation__track_periods` (`period_type=3`) + соседние видимые периоды/кадры.
- **Edge:** непрерывный трек → «разрывов нет»; нет данных → 404.
- **Tests:** `tu-reb` (gap_periods / «разрывов нет»), t2 (`/api/reb/{id}`), t3 (визуализация разрывов).

### #9 · Детекция саботажа (2.2, x4b)
- **Depth:** `v_sabotage` = тёмный DMS-канал/`CAMERA_TAMPER` + `speed_kmh>0`; кнопки «Заявка»/«HR».
- **Edge:** граничные `speed=0`/камера ok → не событие; пустой список → empty-state.
- **Tests:** `tu-sabotage` (правило тёмный DMS+speed>0), t2 (`/api/sabotage`), t3 (виджет).

### #10 · Карта по ролям (2.2, x4b)
- **Depth:** `v_vehicle` (1 ТС = N водителей, роль main/secondary из `driver_trips`); переключатель роли скрывает/показывает слои согласованно во всех экранах; дедуп ТС.
- **Edge:** ТС без вторичного водителя → только main; роль без прав на слой → слой скрыт везде.
- **Tests:** t3 (ролевая видимость + дедуп).
