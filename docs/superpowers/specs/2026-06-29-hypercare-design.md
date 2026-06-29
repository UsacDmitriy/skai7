# Гиперопека (Hypercare) — дизайн-спека

> Статус: **заморожен (Барьер 0)** · Дата: 2026-06-29 · Модуль: `M-HYPERCARE`
> Оркестратор дизайна: Opus 🔴 · Исполнение: Sonnet 🔵 (ШАГ 5)

## 1. Назначение

Новый экран **«Гиперопека»** — плановый и триггерный фотоконтроль транспортных
средств. Гиперопека = система **правил надзора**, где каждое правило описывает:
`триггер (точка отсчёта) → окно (до/после) → частота → набор камер`.
При срабатывании триггера система собирает видео/фото-доказательства вокруг момента.

Семантический предок в системе — действие `request_archive` («запросить архив видео»).
Гиперопека обобщает его до настраиваемого правила поверх существующей видео-инфраструктуры.

## 2. Юзкейсы (каталог)

| # | Триггер | Окно / частота | Камеры | Зачем |
|---|---|---|---|---|
| U1 | Саботаж камеры `CAMERA_TAMPER` | −5м … +2м, непрерывно | все | разбор «что до/после» |
| U2 | Зажигание `ignition_on` | 0…+5м, фото /1м | DMS | предрейсовый фотоконтроль |
| U3 | Резкое падение топлива `Δfuel↓` | −1м … +2м, клип 15с | СНЗ+фронт | подозрение на слив |
| U4 | Подмена водителя `DRIVER_SUBSTITUTION` | 0,+5,+10,+15м, фото | DMS | верификация личности |
| U5 | Удар `CRASH_SENSOR` | −10с … +30с | все | реконструкция ДТП |
| U6 | Вход в REB-зону (GAP) | фото /1м до восстановления GPS | фронт+СНЗ | контроль в «слепой» зоне |
| U7 | Долгий простой `idle>N` | фото /10м | DMS+фронт | нецелевое использование |
| U8 | Ночное движение (22–06) | фото /15м | DMS | анти-усталость |
| U9 | Ручной ad-hoc запрос | произвольное окно | выбор | оперативный контроль |

MVP-триггеры: **событие · датчик · расписание · ручной** (все 4 типа).

## 3. Решения (зафиксировано в Discovery)

- **Данные — гибрид.** Где в `video_events__video_files` есть реальный клип в окне →
  `fulfilled`. Где нет → детерминированный фолбэк `pending` («запрос на регистратор,
  ETA»). Без 5xx офлайн (методология §2.6).
- **Экран — правила + результаты** (двухсекционный).
- **Роль — диспетчер** (дефолт), с ролевой фильтрацией через `RoleProvider`.
- **Движок — подход A**: статический seed-каталог правил + stateless on-demand
  эвалюатор (правила в теле запроса; read-only DuckDB; детерминизм).

## 4. Модель данных (`api/domain/hypercare.py`, Pydantic `extra="forbid"`)

```
VideoChannel = Literal[1, 2, 3, 5]          # 1 ADAS, 5 DMS, 2/3 СНЗ (как в incidents)
TriggerKind  = Literal["event", "sensor", "schedule", "manual"]
EvidenceStatus = Literal["fulfilled", "partial", "pending", "empty"]
ClipStatus   = Literal["available", "pending"]
ClipKind     = Literal["video", "photo"]

class TriggerSpec(BaseModel):              # дискриминируется по kind
    kind: TriggerKind
    alarm_codes: list[str] | None          # kind=event
    metric: Literal["fuel_drop","ignition_on","ignition_off","idle"] | None  # kind=sensor
    op: Literal["lt","gt","lte","gte"] | None
    threshold: float | None
    window_sec: int | None                 # окно наблюдения метрики (sensor)
    interval_min: int | None               # kind=schedule
    time_from: str | None                  # "22:00"
    time_to: str | None                    # "06:00"

class WindowSpec(BaseModel):
    before_sec: int
    after_sec: int
    mode: Literal["continuous", "interval"]
    interval_sec: int | None               # серия фото
    clip_len_sec: int | None               # короткий клип

class HypercareRule(BaseModel):
    id: str
    name: str                              # ru
    enabled: bool
    role_scope: Literal["logist","dispatcher","security","all"]
    trigger: TriggerSpec
    window: WindowSpec
    cameras: list[VideoChannel]

class EvidenceClip(BaseModel):
    channel: VideoChannel
    kind: ClipKind
    offset_sec: int                        # относительно t0 триггера
    status: ClipStatus
    url: str | None                        # available → /api/incidents/{id}/video/{ch}
    eta_sec: int | None                    # pending → детерминированная ETA

class HypercareEvidence(BaseModel):
    id: str
    rule_id: str
    rule_name: str
    vehicle_plate: str
    driver: str | None
    trigger_ts: str                        # ISO
    trigger_label: str
    status: EvidenceStatus
    items: list[EvidenceClip]
```

## 5. API (`api/routers/hypercare.py`, префикс `/api/hypercare`, авто-discovery)

| Метод | Путь | Тело / параметры | Ответ | Негатив |
|---|---|---|---|---|
| GET | `/rules` | — | `list[HypercareRule]` (seed 6–9) | — |
| POST | `/evidence` | `{rules:[HypercareRule], role}` | `list[HypercareEvidence]` | 422 кривое правило · `[]` пусто |
| POST | `/request` | `{vehicle_plate, trigger_ts, before_sec, after_sec, cameras}` | `HypercareEvidence` | 422 |

**Эвалюатор (stateless, детерминированный):** для каждого enabled-правила прогоняет
по `v_incidents` + телеметрии/Fleet Health, ищет реальные клипы в `video_files`,
окно которых пересекается с моментом триггера → `fulfilled`; иначе `pending` с ETA.
Seed = `hash(rule_id, vehicle_plate, trigger_ts)` → повтор даёт идентичный результат.

**Слои:** `routers/hypercare.py` → `services/hypercare_service.py` (эвалюатор +
обогащение) → `repositories/hypercare_repo.py` (параметризованные SQL к
`v_incidents` / `video_events__video_files`). SQL-идентификаторы в двойных кавычках.

## 6. UI-композиция

Страница `web/src/pages/Hypercare.tsx`, маршрут `/hypercare`, lazy + Suspense,
пункт в `NAV` (группа «Мониторинг»), role-scoped (дефолт — диспетчер).

**Секция 1 «Правила надзора»**: грид `RuleCard` (имя, чип триггера = severity-цвет,
сводка окна, тумблер enabled, ⋯-меню). Кнопка «+ Новое правило» → `RuleBuilder`
(drawer-степпер: ①триггер ②окно ③камеры ④имя/роль + live-превью).

**Секция 2 «Собранные доказательства»**: лента `EvidenceCard` (ТС, метка триггера +
время, бейдж статуса) + `EvidenceClipStrip` (миниатюры клипов с бейджами
`available`/`pending`). Клик по `available` → существующий `VideoPlayer` с
`eventMarkerPct` на t0; `pending` → плейсхолдер + ETA + «Повторить».

**Новые файлы фронта:**
- `web/src/pages/Hypercare.tsx`
- `web/src/components/hypercare/{RuleCard,RuleBuilder,EvidenceCard,EvidenceClipStrip}.tsx`
- `web/src/state/hypercareRules.ts` (provider + localStorage, паттерн `state/role.ts`)
- типы в `web/src/api/types.ts`, методы в `web/src/api/client.ts`, фикстуры в `web/src/api/fixtures/`

**Переиспользуем:** `VideoPlayer, Card, Button, SeverityBadge, Timeline, cn`,
токены `--sev-*` / `--color-*`.

**Хранение правил (MVP):** seed-каталог с бэкенда (`GET /rules`); пользовательские
правки (enable/disable, новые правила) — overlay в localStorage по паттерну
`role.ts`. Эвалюация stateless: текущий набор правил уходит в тело `POST /evidence`.

## 7. Цветокодинг

Чип правила = severity триггера: `🔴 critical · 🟠 high · 🟡 medium · 🔵 schedule · ⚪ manual`,
через `SeverityBadge` + токены `--sev-*`.

## 8. Состояния (демо-качество, методология §2.7)

| Состояние | Поведение |
|---|---|
| loading | скелет-карточки (shimmer), как Monitor/EventsFeed |
| empty правила | «Нет правил надзора» + CTA «Создать первое правило» |
| empty результаты | «За выбранный период срабатываний нет» |
| error | баннер «Не удалось загрузить · Повторить», без белого экрана |
| pending-клип | ░-заливка + ⏳ETA + «Повторить ↻» |

## 9. Верификация (`docs/verification-plan.xml` записи)

**Backend `api/tests/test_hypercare_api.py`:**
- `GET /rules` → 200 + `list`, ≥1 правило, схема валидна.
- `POST /evidence` (валидные правила) → 200 + схема; есть и `fulfilled`, и `pending`.
- `POST /evidence` (кривое правило) → 422.
- `POST /evidence` (правило без матчей) → `[]` или `status=empty`.
- Детерминизм: два идентичных запроса → идентичный JSON.
- `POST /request` happy-path → 200; невалидное окно → 422.

**Frontend (vitest + RTL):**
- `Hypercare.test.tsx` — рендер двух секций, список правил и результатов.
- `Hypercare.states.test.tsx` — loading / empty / error.
- `RuleBuilder.test.tsx` — прохождение шагов ①→④, live-превью отражает ввод.
- `EvidenceCard.test.tsx` — рендер `available` (плеер) vs `pending` (ETA-плейсхолдер).

## 10. Сложный UI

Экран попадает под критерии «сложного UI» методологии (новый мультисекционный
экран + конструктор-степпер). Реализация на GLM ведётся по этому макету (раздел 6);
внешний дизайн-инструмент не требуется — макет утверждён в брейншторме.

## 11. Распределение по моделям (предварительно, к ШАГ 4)

| Задача | Файлы | Модель | Инструмент |
|---|---|---|---|
| Домен-схемы | `api/domain/hypercare.py` | DeepSeek 🟣 | ask_deepseek |
| Репозиторий (SQL) | `api/repositories/hypercare_repo.py` | Qwen 🟢 | ask_qwen |
| Эвалюатор (атомарно) | `api/services/hypercare_service.py` | DeepSeek 🟣 | ask_deepseek |
| Роутер | `api/routers/hypercare.py` | Qwen 🟢 | ask_qwen |
| Бэк-тесты | `api/tests/test_hypercare_api.py` | DeepSeek 🟣 | ask_deepseek |
| Страница + компоненты | `web/src/pages/Hypercare.tsx`, `components/hypercare/*` | GLM 🟠 | ask_glm |
| Provider + типы + client + фикстуры | `state/hypercareRules.ts`, `api/*` | GLM 🟠 | ask_glm |
| Фронт-тесты | `*.test.tsx` | GLM 🟠 | ask_glm |
| Барьер волны | — | Opus 🔴 | — |

Оркестратор исполнения: **Sonnet 🔵**. Барьер: **Opus 🔴**.
