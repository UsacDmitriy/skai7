# FEATURES — матрица трассировки фич (идеи #1–#22)

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
> P0-промпты Волны 1 (`b2`/`f4`/`b3`/`d2`) уже выполнены → их DoD/Opus-доработка вынесена в `b14`/`f14` и `b15`/`d6` (Волна 2.1, поверх готового).

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
| #1 | Синк видео↔маркер телеметрии | `track_points`, `TelemetryPoint` §3.1, §6 | b3 **+ b15 (спайн-хардненинг)**, b5 (`get_telemetry`) | f4 IncidentCard **+ f14 (хардненинг)** ; d2 **+ d6 (sync-хардненинг)**/d3 | t3 (sync) | 1 (P0) + 2.1 (f14/b15/d6) | x3 / x4 |
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
| #11 | Умное событие (сцена+кросс-проверка) | `incident_scene`/`incident_weather` §8.1 | b16 (VLM), b17 (Open-Meteo/sun + risk) | f15 scene-card ; d7 | tu-scene, tu-weather | 4.1 | x6 |
| #12 | Прогноз риска + рекомендации | `RiskForecast` §8.4 | b18 (ARIMA+IForest), b22 (нарратив) | f16 forecast-report ; d7 | tu-forecast | 4.1/4.2 | x7 |
| #13 | Fleet Copilot (ассистент) | `CopilotMessage` §8.4 | b21 (tool-use, RU/EN) | f17 copilot-ui | tu-copilot | 4.2 | x7 |
| #14 | РЭБ-геозоны + тепловая карта | `v_risk_zones` §8.1 (incident+reb) | b19 (DBSCAN+РЭБ) | f18 risk-heatmap ; d7 | tu-zones | 4.1/4.2 | x7 |
| #15 | Цепочки усталости | `FatigueChain` §8.4 (YAWNING→DROWSY→harsh) | b20 (оконная корреляция) | (в копилоте/мониторе) | tu-fatigue | 4.1 | x6 |
| #16 | Умный вердикт саботажа | `v_sabotage` + §8 кросс-проверка | b23 (verdict_confidence) | f19 sabotage-verdict | t-wave4-frontend | 4.2 | x7 |
| #17 | AI runtime-governance | флаги/latency/cache §8.6 (`AiFeatureState`) | b24 (флаги/бюджеты/кэш) | (мета во всех AI-блоках) | tu-* (флаг off) | 4.1 | x6 |
| #18 | Измеримость: метрики + data-quality | `AiMetrics`/`DataQuality` §8.7 (`ai_metric_events`) | b25 (агрегация/события; продьюсеры f16/f17/f18) | f21 metrics/data-quality | tu-metrics, t-wave4-frontend | 4.3 | x8 |
| #19 | Explainability: risk-waterfall | `RiskBreakdown` §8.8 (декомпозиция risk_score) | **b27** (`/risk-breakdown` из enrichment) | f20 risk-waterfall | tu-riskbreakdown | 4.3 | x8 |
| #20 | Hardening (foundation) | §8.9: status/CI/security | b26 (auth/audit/throttle) | (—) | t5 (CURRENT_STATUS), t6 (CI+live-smoke), tu-security | 4.3 | x8 |
| #21 | Кросс-сверка скоростей (data trust) | `v_speed_check` §10.3, `SpeedCheck` §10.2 | b29 (`/speed-check`) | f25 (SpeedCheckBadge на карточке) | tu-consistency | 4.4 | x9 |
| #22 | Валидатор консистентности + evidence rate | `v_consistency_checks` §10.3, `ConsistencyReport` §10.2 | b28 (`/api/consistency`) | f25 (ConsistencyPanel на `/metrics`) | tu-consistency | 4.4 | x9 |

> Бэклог/хардненинг, относящийся к фичам: W3-1 (Ticket §7.5 для #6), W3-2 (DIAGNOSTIC для #9-смежного),
> W3-5 (мёртвая ветка «нет видео» для #1/#4) — см. `wave-3-backlog/`.
> **Волна 4 (AI-слой, #11–#16):** офлайн-предрасчёт (VLM/Open-Meteo) → кэш; см. `wave-4-1-smart-context/`,
> `wave-4-2-assistant/`, барьеры `barrier-4-1-*`/`barrier-4-2-*`.

## Per-feature Definition of Done

Ниже — что именно делает каждую фичу «проработанной до максимума» (поверх единого DoD).
Полные контуры полей — в `00-CONTRACT.md`; здесь — фокус на глубине и edge-кейсах.

### #1 · Синк видео↔маркер телеметрии (P0, x3; доработка — `f14`, Волна 2.1)
- **Depth:** при `onTimeUpdate` плеера маркер на `TelemetryChart` движется к точке за `currentTime`; клик по графику перематывает видео (§6).
- **Edge:** нет видео → плеер показывает placeholder, график живёт автономно; пустой `track` → «нет телеметрии», не падать.
- **Реализация глубины:** базовый экран — `f4` (выполнен, Волна 1); состояния/sync/a11y/локали — `wave-2-1-reports-voice/track-f-frontend/f14-incidentcard-hardening`; робастность синк-примитивов (троттлинг/cleanup/петли) — `track-d-design/d6-sync-hardening`; целостность спайна `v_incidents` — `track-b-backend/b15-vincidents-hardening` (всё Opus, Волна 2.1, поверх готового).
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

### #5 · Dispatch alert (2.2, x4b; точка входа — `f23`, Волна 4.3)
- **Depth:** при `auto_request_video=true` — модал с видео ±15с + 3 кнопки действия; телеметрия момента.
- **Edge:** неизвестный `id` → 404 (роутер) / экран «не найдено»; нет видео-окна → плашка.
- **Достижимость (целостность):** триггер из ленты/монитора по `auto_request_video` (по `alarm_code`, overlay через `backgroundLocation`) — `f23` (Волна 4.3); раньше `/alert/:id` был достижим только прямым URL.
- **Tests:** t2 (`/api/alerts/{id}` коды/схема), t3 (модал), f23-триггер (overlay из ленты).

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

### #11 · Умное событие — сцена + кросс-проверка (4.1, x6)
- **Depth:** VLM по кадру → погода/день-ночь/покрытие/видимость; кросс-проверка Open-Meteo+sunrise → флаг расхождения «камера↔погода»; питает `risk_score`.
- **Edge:** нет кадра → `unknown`/`confidence=0`; нет сети → кэш; без кэша → enrichment обратно совместим.
- **Реализация:** `b16` (`incident_scene`) + `b17` (`incident_weather`+надбавка) + `f15`/`d7`. Офлайн-предрасчёт.
- **Tests:** tu-scene (форма/детерминизм), tu-weather (правило расхождения + надбавка + обратная совместимость).

### #12 · Прогноз риска + рекомендации (4.1/4.2, x7)
- **Depth:** ARIMA-тренд 7д + коридор + IsolationForest-аномалия + предписывающие рекомендации; нарратив (b22).
- **Edge:** мало точек → baseline; пустая история → нулевой прогноз; неизвестный plate → 404.
- **Реализация:** `b18` (forecast) + `b22` (нарратив) + `f16`/`d7` (спарклайн+рекомендации).
- **Tests:** tu-forecast (коридор/детерминизм/аномалия/рекомендации).

### #13 · Fleet Copilot — ассистент (4.2, x7)
- **Depth:** LLM tool-use по данным SKAI (incidents/reports/forecast/zones/fatigue/sabotage), RU/EN; ответ + данные.
- **Edge:** нет ключа/сети → детерминированный фолбэк-роутинг; мусор → вежливый дефолт; язык по тексту.
- **Реализация:** `b21` (copilot_service) + `f17` (чат-панель, a11y/состояния).
- **Tests:** tu-copilot (фолбэк-роутинг + язык + graceful default).

### #14 · РЭБ-геозоны + тепловая карта (4.1/4.2, x7)
- **Depth:** DBSCAN-кластеры алярмов (`incident`) + зоны GPS-jamming (`reb`); прогноз по часу; тепловой слой на мониторе.
- **Edge:** нет точек → `[]`/пустой слой; фильтры kind/hour/роль согласованы; много точек → throttle.
- **Реализация:** `b19` (`v_risk_zones`+`/zones`) + `f18`/`d7` (`RiskHeatLayer`). Дифференциатор (РЭБ — белое пятно рынка).
- **Tests:** tu-zones (детерминизм кластеров, оба kind, фильтры).

### #15 · Цепочки усталости (4.1, x6)
- **Depth:** оконная корреляция `YAWNING→DROWSY→harsh` по водителю/рейсу → раннее предупреждение; `severity` по длине/тяжести.
- **Edge:** события вне окна/одиночные → не цепочка; нет цепочек → `[]`; без `Date.now()`.
- **Реализация:** `b20` (`/fatigue`); потребитель — копилот/монитор.
- **Tests:** tu-fatigue (внутри/вне окна, монотонность severity, фильтр).

### #16 · Умный вердикт саботажа (4.2, x7)
- **Depth:** тёмный DMS+speed>0 (текущее) усилен кросс-проверкой сцены: «день/ясно» снаружи ⇒ confidence↑; «ночь/туман» ⇒ объяснимо.
- **Edge:** нет `incident_scene`/`incident_weather` → прежний вердикт `v_sabotage` (обратная совместимость).
- **Реализация:** `b23` (`verdict_confidence`/`verdict_reason`) + `f19` (UI вердикта).
- **Tests:** t-wave4-frontend (виджет вердикта) + регресс tu-sabotage.

> **Дополнения по второму research-отчёту (#17–#20)** — слой измеримости/управляемости/explainability +
> foundation. **Реорганизация:** #17 (governance) — runtime-основа в **Волне 4.1**; #18–#20 (метрики/
> explainability/hardening) вынесены в новую под-волну **4.3 «AI Ops & Trust»** (барьер **x8** → main).
> Каркас (типы/маршруты/`ai_metric_events`/CI) готовит **подготовка Волны 3** (`w3-16…19`).

### #17 · AI runtime-governance (4.1, x6)
- **Depth:** feature-flags на каждую AI-фичу + latency-budget + offline-cache policy/TTL; мета `AiFeatureState{source,latency_ms}`.
- **Edge:** флаг off → «disabled» (200, не падение); нет сети/превышен бюджет → `source=cache/fallback`.
- **Реализация:** `b24` (`ai_flags.py`/`ai_runtime.py`). Кросс-режущая основа для b16–b23.
- **Tests:** tu-* с флагом off; регресс с флагом on зелёный.

### #18 · Измеримость: метрики + data-quality (4.3, x8)
- **Depth:** `AiMetrics` (acceptance/tool-success/mismatch/zone-hit/time-to-triage/coverage) + `DataQuality` (camera-offline/missing-gps-media/mismatch).
- **Edge:** пустые события → нулевые дефолты; `*_ratio ∈ [0,1]`.
- **Реализация:** `b25` (`/metrics/ai`,`/metrics/data-quality`,`ai_metric_events`) + `f21` (`/metrics` экран).
- **Tests:** детерминизм агрегации на тестовых событиях; t-wave4-frontend (панель).

### #19 · Explainability: risk-waterfall (4.3, x8)
- **Depth:** `RiskBreakdown` — вклад severity/speed/night/weather/freq, сумма = `risk_score`; waterfall на карточке/в отчёте.
- **Edge:** нет `weather_bonus` (без кэша) → вклад 0, не ломается; сумма всегда сходится с API.
- **Реализация:** `b27` (`GET /api/incidents/{id}/risk-breakdown`, детерм. из enrichment) + `f20` (`RiskWaterfall`).
- **Tests:** сумма вкладов = risk_score; t-wave4-frontend.

### #20 · Hardening — foundation (4.3, x8)
- **Depth:** единый `CURRENT_STATUS.md` (анти-дрейф), remote CI + **nightly live-API smoke** (анти-fixture-маскировка), security baseline (auth/audit/throttle, SLO).
- **Edge:** `SKAI_SECURITY_ENABLED` не задан (дефолт `false`, демо) → как раньше; live-smoke краснеет при backend-регрессе, который fixtures скрывают.
- **Реализация:** `t5` (`gen_status.py`/`CURRENT_STATUS.md`), `t6` (`.github/workflows/*`), `b26` (`security.py`/`audit.py`/`SLO.md`).
- **Tests:** CI зелёный; live-smoke на `VITE_USE_FIXTURES=false`; audit пишет `output/audit.csv`.

> **Волна 4.4 «Data Trust» (#21–#22)** — консистентность данных, главный блокер доверия из клиентских
> интервью: Фомин (PepsiCo) — расхождение скоростей видео↔телематика, «39 ДТП → видео подтвердило 5»;
> Маслов (Балтика) — дубли терминалов. Контракт — **§10** (аддендум). Конкурентный паттерн — Lytx
> review-queue (`COMPETITORS.md`). Без AI: детерминированный SQL.

### #21 · Кросс-сверка скоростей — data trust per incident (4.4, x9)
- **Depth:** на каждом инциденте сравнение скорости из события (`"Speed"` алярма) и GPS-трека (ближайшая
  точка ±10 с); `delta` → `ok`/`minor`/`major`; `truth_source='gps_track'` (ASSUMPTION §10.2: CAN-данных нет).
- **Edge:** нет точки в окне/нет скорости события → `no_data` (200, не 5xx); пустые координаты не валят view;
  детерминизм (повторный вызов байт-идентичен).
- **Реализация:** `b29` (`/api/incidents/{id}/speed-check`, `35_v_speed_check.sql`) + `f25` (`SpeedCheckBadge`
  на карточке рядом с f15-чипом; в UI «GPS-трек», не «CAN»).
- **Tests:** tu-consistency (`test_speed_check.py`): окно ±10 с (9 с берёт / 11 с нет), табличные пороги, 404, `no_data`.

### #22 · Валидатор консистентности + evidence rate (4.4, x9)
- **Depth:** 7 канонических кросс-датасетных проверок (§10.3): ТС без трека, инцидент без видео
  (→ `evidence_rate` — метрика Фомина 5/39), дубли терминалов (Маслов), покрытие vehicle_matches,
  монотонность таймстемпов, валидность координат, расхождение скоростей (→ `speed_agreement_rate`).
- **Edge:** пустой источник → `total=0, ratio=0, ok`; статусы в сервисе (fail >0.2 / warn >0 / ok);
  `sample_ids` ≤ 5; все `ratio ∈ [0,1]`.
- **Реализация:** `b28` (`/api/consistency`, `34_v_consistency.sql`) + `f25` (`ConsistencyPanel` на `/metrics`
  ниже f21-панели).
- **Tests:** tu-consistency (`test_consistency.py`): границы статусов, инварианты `evidence_rate`/`speed_agreement_rate`, детерминизм, датасет-факт пустых координат.
