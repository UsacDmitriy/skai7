# f25 · Data-Trust UI — бейдж сверки скоростей + панель консистентности (фичи #21/#22)

> Трек **Frontend**. Против `00-CONTRACT.md` §10.2/§10.4/§10.5. **Владеет:**
> `web/src/components/ai/SpeedCheckBadge.tsx`, `web/src/components/ai/ConsistencyPanel.tsx`;
> **аддитивные** правки `web/src/pages/IncidentCard.tsx`, `web/src/pages/Metrics.tsx`,
> `web/src/api/types.ts`, `web/src/api/client.ts`, `web/src/api/fixtures.ts`.
> **Исполнение:** bounded ClinePass package; role `worker`; route category `code`; exact route/model only from `tools/clinepass-mcp/models.env` — компоненты против контракта; гейт = typecheck + vitest.
> **Волна 4.4**, окно 2 (web). Зависит от: b28/b29 (эндпоинты §10.1), f15 (точка вставки в карточке),
> f21 (точка вставки в метриках). Запускается после b29.

## Цель

Показать слой доверия к данным там, где работает диспетчер: на карточке инцидента — сверка скоростей
двух источников (кейс Фомина), на экране метрик — светофор консистентности датасетов (кейс Маслова).

## Состав

1. **Типы** (`web/src/api/types.ts`, аддитивно): `ConsistencyCheck`, `ConsistencyReport`, `SpeedCheck` —
   **дословно по §10.2** (поля/литералы статусов).
2. **Клиент** (`web/src/api/client.ts`, аддитивно, за тем же свитчем `USE_FIXTURES`, паттерн соседних методов):
   `getConsistency(): Promise<ConsistencyReport>` → `GET /api/consistency`;
   `getSpeedCheck(id: string): Promise<SpeedCheck>` → `GET /api/incidents/${id}/speed-check`.
3. **Фикстуры** (`web/src/api/fixtures.ts`): `ConsistencyReport` с 7 проверками (минимум одна `warn`,
   одна `fail`); `SpeedCheck` — три кейса: `ok` (32/28.4), `major` (90/61), `no_data` (все null).
4. **`SpeedCheckBadge.tsx`** — вставить в `IncidentCard.tsx` **рядом с `SceneContextChip` (f15)**:
   - текст: «Скорость: событие {event} · GPS {track} → совпадает» (`ok`), «…→ расходится (±{delta})»
     (`minor`/`major`), «Скорость: нет данных GPS-трека» (`no_data`);
   - тон: `ok` — нейтральный/успех, `minor` — warning, `major` — danger, `no_data` — muted;
   - tooltip: «Источник истины — GPS-трек (CAN-данных в датасете нет, §10.2)»;
   - состояния loading/error — тихо скрыть бейдж (не ломать карточку), как у f15-чипа.
5. **`ConsistencyPanel.tsx`** — вставить в `Metrics.tsx` **ниже `DataQualityPanel` (f21)**:
   - заголовок «Консистентность данных»; сводные `evidence_rate`/`speed_agreement_rate` (проценты);
   - 7 строк-проверок: светофор по `status`, `title_ru`, `affected_count`/`total`, `sample_ids`
     (до 5, моноширинно); `description_ru` — вторичным текстом;
   - пустой/ошибочный ответ → панель с заглушкой «нет данных», не падение.
6. **A11y:** светофор не только цветом (иконка/текст статуса); бейдж — `title`/`aria-label`.
7. Никакого `AiFeatureState`/`ai_flags` — это не AI-блок (§10.0): без governance-меты.

## Check

- На карточке инцидента с треком виден бейдж сверки; на инциденте без точек — «нет данных» (не пусто/не краш).
- `/metrics` показывает панель консистентности под data-quality; светофор и доли совпадают с
  `curl -s localhost:8000/api/consistency`.
- Паритет фикстур: `VITE_USE_FIXTURES=true` — те же состояния (включая `major` и `no_data` кейсы).
- В UI написано «GPS-трек», НЕ «CAN» (ASSUMPTION §10.2).
- `npm run typecheck` зелёный; vitest: рендер бейджа для `ok`/`major`/`no_data`, рендер панели на фикстуре,
  отсутствие краша при error-ответе.
- Существующие тесты карточки/метрик зелёные (правки аддитивны).

## Коммит (обязательно)

Заверши промпт коммитом в свою ветку — **merge на барьере берёт только коммиты**:

```bash
# параллельно с tu-consistency в соседнем worktree — стейджи только свои файлы (НЕ git add -A)
git add web/src/components/ai/SpeedCheckBadge.tsx web/src/components/ai/ConsistencyPanel.tsx web/src/pages/IncidentCard.tsx web/src/pages/Metrics.tsx web/src/api/types.ts web/src/api/client.ts web/src/api/fixtures.ts
git commit -m "f25: Data-Trust UI — бейдж сверки скоростей + панель консистентности (§10)"
```
