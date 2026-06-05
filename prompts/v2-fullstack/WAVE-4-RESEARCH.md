# Волна 4 — методология анализа и трассировка решений

> Подробный разбор: **как** я рассуждал, **где и что** искал, **как** сравнивал, **что** нашёл и
> **как** применил к промптам Волны 4. Документ — спутник к `WAVE-4` (см. `wave-4-1-smart-context/`,
> `wave-4-2-assistant/`, контракт `00-CONTRACT.md §8`, трассировка `FEATURES.md #11–#16`).
>
> Дата анализа: 2026-06-05. Ветка: `integration`.

---

## 0. Постановка задачи (что просили)

1. Ещё раз проанализировать source-папку.
2. Проанализировать конкурентов — минимум 10.
3. Продумать оригинальные решения (боты/ассистенты; «умное событие» по снимку → погода/время суток/
   внешние условия; внешние API для сравнения; по отчётам — прогнозирование и рекомендации).
4. Последовательно презентовать идеи.
5. Подготовить промпты и положить в Волну 4 (или несколько подволн).

**Критерий фич:** новое · актуальное · доступное. **Требование:** многогранный анализ, а не генерация
«что попало».

---

## 1. Методология (как я работал)

### 1.1 Процессная рамка

- Работал в **plan mode** (без правок системы до утверждения) по связке *brainstorming → plan workflow*:
  исследование → синтез → презентация → уточнения → план → утверждение → исполнение.
- Принцип: **сначала факты, потом идеи.** Идеи генерировал только после привязки к (а) реальным данным
  репозитория, (б) пробелам рынка, (в) доступным бесплатным кирпичам — чтобы каждая фича была
  обоснованной, а не «модной».

### 1.2 Инструменты и три параллельных потока

Запустил **3 Explore-агента одновременно** (каждый со своим узким мандатом), чтобы покрыть три грани:

| Поток | Агент | Инструменты | Мандат |
|---|---|---|---|
| A. Source | Explore #1 | Read/Grep/Glob по диску | Реальный код/данные SKAI: какие **сигналы** есть, что реализовано, ограничения |
| B. Конкуренты | Explore #2 | **WebSearch + WebFetch** | ≥12 вендоров (глобал + СНГ): AI-фичи, ассистенты, прогнозы, доступность, **белые пятна** |
| C. Тренды/API | Explore #3 | **WebSearch + WebFetch** | Актуальные AI-техники + **бесплатные** API/модели; что реально для офлайн-демо |

Почему параллельно и почему разными агентами: разделение мандатов даёт **независимые перспективы**
(агент по конкурентам «не знает» про ограничения данных и наоборот) — это снижает подгонку выводов и
ускоряет (3 потока вместо одного длинного).

> MCP для скрапинга **не ставил** — встроенных `WebSearch`/`WebFetch` хватило, и в plan mode установка
> запрещена. Это read-only веб-доступ; для самих фич Волны 4 внешние сервисы — бесплатные HTTP-API без
> ключей (Open-Meteo, sunrise-sunset), так что отдельный скрапинг-MCP не нужен.

---

## 2. Анализ source-папки (поток A)

### 2.1 Что и где смотрел

- **Контракт/домен:** `prompts/v2-fullstack/00-CONTRACT.md` (§1–§7), `FEATURES.md` (идеи #1–#10),
  `init/context/*` (DESIGN.md/роли).
- **Реальные данные:** `data/`, `datasets/ready/**`, `data/analysis/alarm_types.json`, `data/seed/*`,
  `data/mock/`.
- **Реализация:** `api/` (routers/services/domain/`core/enrichment.py`/`sql/*.sql`/`etl/*`),
  `web/` (`src/pages/*`, `src/components/*`, `src/api/*`).

### 2.2 Что нашёл — доступные сигналы (ключ к осуществимости)

| Сигнал / таблица | Поля | Объём | Реальные/мок |
|---|---|---|---|
| Алярмы `selected_video_alarms` | AlarmId, Type, plate, Begin/End, Speed, Address, VideoCount, lat/lon | **54** | реальный CSV |
| Видео `video_files` | alarm_id, **channel {1 ADAS,5 DMS,2,3}**, media_relative_path, download_status | **94** | реальный CSV |
| Телеметрия `track_points` | alarm_id, point_index, lat/lon, **speed, timestamp** | **6 635** | реальный CSV |
| Сводка трека `track_summary` | mileage_km, movement_duration | 54 | реальный CSV |
| Каталог алярмов `alarm_types.json` | code, label_ru, **source {DMS/ADAS/TELEMATICS/COMBINED/DIAGNOSTIC}**, severity | **14 типов** | мок JSON |
| Справочник водителей `driver_reference` | plate, driver, phone, department, region, safety_score | 21 | сид |
| Навигация/РЭБ `navigation__track_periods` | **period_type {1,2,3}** (3 = GPS-jamming), lat/lon, speed | ~423 / ~82k точек | реальный CSV |
| Топливо/сенсоры | fuel_*, sensor_* | сотни строк | реальный CSV, **не интегрированы (501)** |

**Enrichment** (`api/core/enrichment.py`, детерминированно): `risk_score = clamp(100·(0.45·sev_w +
0.25·speed_ratio + 0.15·night + 0.15·freq_w))`, `is_night`, `speed_limit_for`, `events_last_7d`,
`confidence`, `ax`, `cameras[]`.

### 2.3 Что нашёл — ограничения (определили подход к API)

- Данные **исторические** (май 2026), **нет live-флота/реал-тайма**.
- Демо **офлайн/детерминированно:** `VITE_USE_FIXTURES`, без `random`/`datetime.now()`,
  STT локально (whisper), NLU = Groq **+ regex-фолбэк без сети**.
- Вывод, повлиявший на дизайн: **любая внешняя интеграция (VLM, погода) должна уметь работать офлайн →
  предрасчёт+кэш.** Это стало сквозным принципом Волны 4.

---

## 3. Анализ конкурентов (поток B)

### 3.1 Метод сравнения

- Поиск по сегментам: «video telematics AI», «driver monitoring DMS/ADAS», «fleet AI assistant»,
  «predictive fleet safety», плюс СНГ-вендоры по названиям.
- Для **каждого** вендора фиксировал 6 измерений: сегмент/регион · AI/CV-ядро · **бот/ассистент** ·
  **прогноз/forecasting** · доступность (SaaS/API/free) · источник (URL).
- Затем два среза: **table-stakes vs differentiating** (что уже у всех / что редко) и **gap-analysis**
  (чего нет ни у кого = белые пятна для SKAI).

### 3.2 Кого проанализировал (18 вендоров)

**Глобал:** Samsara, Motive, Lytx, Netradyne, Nauto, Cambridge Mobile Telematics (CMT), Geotab,
Verizon Connect, Webfleet (Bridgestone), Cipia, Nexar, Azuga, Zonar.
**СНГ/Россия:** Wialon (Gurtam), Omnicomm, GLONASSsoft, СКАУТ, ТехноКом/АвтоГРАФ, ЭРА-ГЛОНАСС.

### 3.3 Ключевые находки по измерениям

- **AI/CV (table-stakes):** двойная камера, детекция отвлечения/сонливости/ремня, коучинг — почти у всех
  глобал-вендоров. У СНГ-вендоров AI/CV в основном **отсутствует** (классическая телематика GPS/ГЛОНАСС).
- **Бот/ассистент (редко):** только **Motive Atlas** (голос «Hey Motive») и **Geotab Ace** (NL-копилот).
  **Двуязычных RU — нет.**
- **Прогноз/forecasting (редко):** **Nauto** (предсказание столкновений, VERA-score), **CMT DriveWell
  Atlas** (foundation-model), Verizon (emerging). **Трендового прогноза риска «по неделям» — нет ни у кого.**
- **Понимание сцены/среды:** только **Webfleet + Peregrine.ai** (погода/дорога/красный свет).
- **РЭБ/GPS-jamming:** упоминается лишь как лог-событие (Geotab); **как фича безопасности не упакован ни у кого.**

### 3.4 Сводная таблица (фрагмент)

| Вендор | Регион | AI/CV | Ассистент | Прогноз |
|---|---|---|---|---|
| Samsara | Глобал | 30+ детекций | NL-чат (огранич.) | scoring, без предсказания столкновений |
| Motive | Глобал | 30+ моделей, стерео | **Atlas (голос)** | коучинг |
| Lytx | Глобал | MV+AI ~95%, ~100 паттернов | алерты | предиктивный риск |
| Nauto | Глобал | предсказание столкновений | — | **VERA risk (предиктив)** |
| CMT | Глобал | **DriveWell Atlas (foundation)** | — | crash-prediction |
| Geotab | Глобал | GO Focus AI | **Ace (NL-копилот)** | предиктив. ТО/коллизии |
| Webfleet | EMEA | CAM + **Peregrine (среда)** | — | OptiDrive |
| Wialon/Omnicomm/СКАУТ/… | СНГ | классическая телематика | — | **нет** |

### 3.5 Белые пятна (gap-analysis) — главный вывод

Перечислил пробелы; **жирным** — те, что лягут в Волну 4:

1. **Кросс-проверка «камера ↔ внешние данные» — не делает НИКТО.** ← идея #11
2. **Трендовый прогноз риска + предписывающие рекомендации — почти нет.** ← идея #12
3. **Двуязычный (RU/EN) разговорный копилот — нет.** ← идея #13
4. **РЭБ/GPS-jamming как фича (зоны/прогноз) — нет.** ← идея #14
5. Детекция саботажа/tamper с обоснованным вердиктом — слабо. ← идея #16
6. Цепочки-предвестники (усталость до инцидента) — не выделяют. ← идея #15 (своя находка, см. §5)
7. Chain-of-custody видео, cost-of-safety ROI — есть в литературе, но не у мейнстрима (вне скоупа Волны 4).

### 3.6 Источники (выборка URL)

Samsara `samsara.com` · Motive `gomotive.com/products/dashcam` · Lytx `lytx.com/.../mv-ai-technology` ·
Netradyne `netradyne.com` · Nauto `nauto.com` (+ `nauto.com/vtti/risk-fusion-report`) ·
CMT `cmtelematics.com/.../drivewell-atlas` · Geotab `geotab.com/press-release/geotab-ace-news` ·
Verizon `verizonconnect.com/.../fleet-technology-trends-report` ·
Webfleet/Peregrine `peregrine.ai/webfleet-and-peregrine-ai-collaborate-...` · Cipia `cipia.com/news/...` ·
Nexar `fleet.getnexar.com` · Azuga `azuga.com` · Zonar `zonar.com` · Wialon `wialon.com/.../russian-telematics-market` ·
Omnicomm `omnicomm-world.com` · СКАУТ `scout-gps.ru` · АвтоГРАФ `tk-nav.com` · ЭРА-ГЛОНАСС `glonassunion.ru/era-glonass`.

> Достоверность: часть утверждений — маркетинг вендоров; при сомнении формулировал осторожно
> («почти никто», «emerging»). Цифры эффективности (−40 % аварий и т.п.) — заявления вендоров, не аудит.

---

## 4. Анализ AI-трендов и доступных API (поток C)

### 4.1 Что искал

Под каждый блок задачи — актуальные техники (2024–2026) **и** их доступные/бесплатные реализации, с
фокусом на **офлайн-feasibility** (демо детерминированно).

### 4.2 Что нашёл

**(a) Сцена по кадру (VLM):**
- **Florence-2** (Microsoft, 0.23–0.77B, локально, free), **Moondream 2/3** (edge, free),
  **BLIP-2 + LoRA** (дообучение под дашкам), облачные **GPT-4o-mini / Claude vision** как fallback.
- Вывод: погода/день-ночь надёжны (>95 %), покрытие дороги — слабее → использовать как **enrichment-слой**,
  не как первичный классификатор. Для демо — **разовый офлайн-прогон → кэш**.

**(b) Бесплатные API кросс-проверки (по `ts`+`lat/lon`):**
- **Open-Meteo** `historical-forecast-api.open-meteo.com/v1/forecast` — погода/осадки/видимость,
  **без ключа**, история, 10k запросов/день.
- **sunrise-sunset.org** `api.sunrise-sunset.org/json` — рассвет/закат/сумерки → истинный день/ночь,
  **без ключа**. (Альтернатива — расчёт solar elevation.)
- Air Quality (AQICN/Open-Meteo) — опционально.

**(c) Прогноз/рекомендации:**
- **ARIMA** (statsmodels) — тренд счётчиков нарушений; **IsolationForest** (sklearn) — аномалии;
  гибрид «ARIMA-прогноз + IForest-резидуалы» снижает ложные срабатывания. Всё **free, офлайн,
  детерминированно** (fixed `random_state`). Рекомендации — правила + опц. LLM-нарратив.

**(d) Копилоты:**
- **Groq LLaMA 3.3 70B** (уже в стеке через `nlu_service`) — free-tier, OpenAI-совместимый, function-calling.
- **Ollama** (локально) — офлайн-фолбэк. Паттерн: LLM + tool-use над **своими** эндпоинтами + RAG.

### 4.3 Источники (выборка)

Florence-2 `blog.roboflow.com/florence-2` · Moondream `blog.roboflow.com/moondream-2` ·
Open-Meteo `open-meteo.com/en/docs/historical-forecast-api` · Sunrise-Sunset `sunrise-sunset.org/api` ·
ARIMA-anomaly `medium.com/.../time-series-anomaly-detection-with-arima` ·
Geotab predictive `geotab.com/blog/predictive-safety-model-fleet-collisions` ·
Groq `groq.com/pricing` · Ollama `sitepoint.com/local-llms-complete-guide`.

---

## 5. Синтез идей — критерии и отбор

### 5.1 Критерии (от пользователя)

- **Новое** — не table-stakes; закрывает белое пятно (§3.5).
- **Актуальное** — техника 2024–2026 (§4).
- **Доступное** — free/в стеке, и **офлайн-feasible** на данных SKAI (§2).

### 5.2 Формула отбора: пробел × данные × free-кирпич → идея

| Белое пятно (§3.5) | Данные SKAI (§2.2) | Free-кирпич (§4.2) | → Идея |
|---|---|---|---|
| Кросс-проверка камера↔данные | кадр ch1/ch5, `ts`+`lat/lon` | VLM + Open-Meteo + sunrise | **#11 Умное событие** |
| Трендовый прогноз | `events_last_7d`, история по plate | ARIMA + IForest | **#12 Прогноз + рекомендации** |
| Двуязычный копилот | существующие эндпоинты + `nlu_service` | Groq tool-use + фолбэк | **#13 Fleet Copilot** |
| РЭБ как фича | `period_type=3`, lat/lon | DBSCAN | **#14 Геозоны + heatmap** |
| Tamper-вердикт | `v_sabotage` + сцена #11 | правило confidence | **#16 Умный вердикт** |
| (своя находка) предвестники | каталог `YAWNING/DROWSY/harsh` + `ts` | оконная корреляция | **#15 Цепочки усталости** |

> **#15 — собственная находка** (не из конкурентов): каталог из 14 типов содержит «предвестники»
> усталости (зевание→микросон→резкое торможение). Никто не связывает их в цепочку как раннее
> предупреждение — а данные ровно это позволяют. Это и есть «найди что-то ещё интересное».

### 5.3 Что НЕ взял (и почему)

- Chain-of-custody на блокчейне, cost-of-safety ROI — есть пробел, но требуют внешних систем/допущений,
  слабо вписываются в офлайн-демо. Вынес в «стретч».
- Driver-facing коучинг-бот в кабине — у SKAI нет in-cab устройства (только ops-дашборд) → не feasible.

---

## 6. Применение к промптам (трассировка finding → prompt)

### 6.1 Сквозные дизайн-решения (откуда взялись)

| Решение | Источник вывода |
|---|---|
| **Предрасчёт+кэш** для VLM/API (`data/ai/*.json`, таблицы `incident_scene`/`incident_weather`) | §2.3 (офлайн/детерминизм) + §4.2a (VLM как enrichment) |
| **Подволны 4.1/4.2 + барьеры** | паттерн Волны 2 в репо (консистентность) |
| **Контракт-первый (`§8`)** | конвенция репо: кодим против `00-CONTRACT.md` |
| **Модель-разметка Opus/Sonnet/Qwen** | прод-критерий из прошлых волн (на сложном не экономим) |
| **Секции `## Коммит` + GUARD в `x6/x7`** | ранее закрытый разрыв «незакоммиченное на барьере» |
| **Переиспользование** `enrichment.py`/`nlu_service`/`v_sabotage`/`Report.tsx`/`Monitor.tsx` | §2.2 (что уже реализовано) |

### 6.2 Идея → промпты → модель → переиспользование

| Идея | Backend | Frontend/Design | Тесты | Модель (сложн.) | Переиспользует |
|---|---|---|---|---|---|
| #11 Умное событие | `b16` scene (VLM, предрасчёт), `b17` weather-crosscheck + risk | `f15` scene-card, `d7` chips | `tu-scene`,`tu-weather` | b16/b18/b19 🔴 | `enrichment.risk_score`, кадры ch1/ch5, `v_incidents` |
| #12 Прогноз | `b18` forecast (ARIMA+IForest), `b22` нарратив | `f16` forecast-report, `d7` sparkline | `tu-forecast` | b18 🔴 | `events_last_7d`, `reports_service` |
| #13 Копилот | `b21` copilot (tool-use, RU/EN) | `f17` copilot-ui | `tu-copilot` | b21/f17 🔴 | `nlu_service` (расширение), все эндпоинты как tools |
| #14 Геозоны/heatmap | `b19` zones (DBSCAN+РЭБ) | `f18` risk-heatmap, `d7` heat-layer | `tu-zones` | b19/f18 🔴 | `v_incidents` lat/lon, `navigation__track_periods`, Leaflet/`components/map` |
| #15 Усталость | `b20` fatigue-chain | (копилот/монитор) | `tu-fatigue` | b20 🔵 | каталог алярмов, `ts` |
| #16 Вердикт саботажа | `b23` verdict (confidence) | `f19` verdict-UI | `t-wave4-frontend` | b23 🔵 | `v_sabotage` (§7.5) + сцена #11 |

### 6.3 Как конкретные находки попали в текст промптов

- **Open-Meteo/sunrise (§4.2b)** → дословно в `b17` («Open-Meteo historical … sunrise-sunset.org или
  расчёт solar elevation», кэш `data/ai/weather_cache.json`) и в контракт `§8.1` (`incident_weather`).
- **Florence-2/Moondream/облачный VLM (§4.2a)** → в `b16` («локальный Florence-2/Moondream ИЛИ Groq/
  Claude vision — выбор в конфиге», VLM **только в `scene_precompute.py`**, не в рантайме).
- **ARIMA+IsolationForest (§4.2c)** → в `b18` (сигнатуры, `random_state`, baseline-фолбэк) и `tu-forecast`
  (инвариант коридора `ci_low ≤ predicted ≤ ci_high`, детерминизм, аномалия).
- **DBSCAN + `period_type=3` (§2.2/§4.2c)** → в `b19` (haversine-DBSCAN, два `kind` incident/reb) и `§8.1`.
- **Каталог-предвестники (§2.2)** → в `b20` (коды `DMS_YAWNING/DMS_DROWSY/HARSH_*`, окно `window_min`).
- **Groq + фолбэк-паттерн `nlu_service` (§2.2/§4.2d)** → в `b21` (ветка Groq function-calling + детермин.
  regex-роутинг RU/EN; «никогда не падает» — как у nlu).
- **Белое пятно РЭБ (§3.5)** → отдельный слой `kind=reb` в `b19`/`f18` (явный дифференциатор).
- **Офлайн-вывод (§2.3)** → в каждый `Check`: «без сети читает кэш», «фолбэк без падений»; и в `x6`/`x7`
  («работает офлайн без сети/ключей»).

### 6.4 Контракт как точка фиксации

Все находки, требующие межтрековой согласованности, заморожены в **`00-CONTRACT.md §8`**: таблицы
(`incident_scene`/`incident_weather`/`v_risk_zones`), эндпоинты (`/scene`,`/forecast`,`/zones`,
`/fatigue`,`/copilot/chat`), схемы (`SceneContext`/`WeatherCrossCheck`/`RiskForecast`/`RiskZone`/
`FatigueChain`/`CopilotMessage`) — чтобы backend/frontend/tests кодили против одного источника истины.

---

## 7. Артефакты и верификация

**Создано:** 23 промпта Волны 4 (15 🔵 + 8 🔴) + 4 README + 2 барьера; расширены `00-CONTRACT.md §8`,
`FEATURES.md (#11–#16 + DoD)`, `EXECUTION.md` (раздел + mermaid + легенда **7/43/30 = 80**), `README.md`.

**Проверки (Python, т.к. ugrep ложно реагировал на `\*\*`):** все 23 промпта — с модель-тегом и секцией
`## Коммит`; `x6`/`x7` содержат GUARD; mermaid сбалансирован (subgraph 30 / end 30). Физически 84 файла
с тегом = 80 логических + 4 дубликата барьерных копий (`x2`×4/`x3`×2 по папкам).

**Коммиты:** `51ab473` (Волна 4) и предшествующие — на `origin/integration`. Волны 1–3 не тронуты.

---

## 8. Честная оценка достоверности

- **Точно (проверяемо):** инвентарь данных SKAI (§2) — читал файлы на диске; список эндпоинтов/таблиц.
- **Веб-исследование (§3–§4):** факты с источниками-URL; часть — маркетинг вендоров (помечал осторожно).
  Цифры эффективности конкурентов — их заявления, не независимый аудит.
- **VLM-точность сцены** — эмпирически не замерял на данных SKAI; рекомендация опирается на литературу
  (>95 % для погоды/день-ночь) → поэтому VLM позиционирован как enrichment + ручная проверка кэша.
- **Прогноз на 54 алярмах** — данных мало; в `b18` явно заложен baseline-фолбэк при нехватке точек.
- Это **план/спека**: промпты исполнятся моделями позже; реальное качество фич подтвердит барьерный smoke
  (`x6`/`x7`), а не этот документ.

---

> Связанные файлы: `00-CONTRACT.md §8` · `FEATURES.md #11–#16` · `EXECUTION.md` (раздел «Волна 4») ·
> `wave-4-1-smart-context/**` · `wave-4-2-assistant/**` · `barrier-4-1-smart-context/x6` ·
> `barrier-4-2-assistant/x7`. План-файл сессии: `~/.claude/plans/purring-watching-parnas.md`.

---

## 9. Сверка со вторым research-отчётом (внешний)

Получен второй независимый deep-research отчёт по `UsacDmitriy/skai7` (построен частично **на этом**
документе). Сверка с текущим скоупом Волны 4:

**Подтверждает (overlap):** те же 6 идей (#11–#16), те же кирпичи (Open-Meteo/sunrise/ARIMA+IsolationForest/
DBSCAN/Groq), тот же подход precompute+cache, та же декомпозиция (scene_precompute, copilot intent-router +
registry-tools, ForecastService+RecommendationEngine+NarrativeRenderer, REB DBSCAN по `period_type=3`).
Две независимые работы сошлись → скоуп выбран верно.

**Дельта (добавлено в Волну 4, #17–#20):** слой измеримости/управляемости/explainability + foundation —
то, чего в исходной Волне 4 не было:

- **#17 governance** (`b24`): feature-flags + latency-budget + offline-cache policy/TTL, мета `AiFeatureState`.
- **#18 метрики/data-quality** (`b25`,`f21`): `/api/metrics/ai` + `/api/metrics/data-quality` (acceptance/
  tool-success/mismatch/zone-hit) — «как мы знаем, что фичи помогают».
- **#19 risk-waterfall** (`f20`): декомпозиция `risk_score` (`RiskBreakdown` §8.8) — explainability почти бесплатно.
- **#20 hardening** (`t5`/`t6`/`b26`): единый `CURRENT_STATUS.md` (анти-дрейф), remote CI + **nightly live-API
  smoke** (анти-fixture-маскировка), security baseline (auth/audit/throttle, SLO).
- Усилены: `b21` copilot (audit-trail + цитирование фактов + latency + флаг), барьер `x7` (live-smoke).

**Также отмечено отчётом (учтено как риски/принципы, не отдельные промпты):** дрейф источников истины,
fixture-mode маскирует backend-регресс (→ live-smoke в `t6`/`x7`), малый объём данных для AI (→ baseline-first +
confidence bands, уже в `b18`).

