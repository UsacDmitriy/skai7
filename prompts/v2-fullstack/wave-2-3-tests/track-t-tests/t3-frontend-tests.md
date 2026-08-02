# T3 · Frontend-тесты (vitest + React Testing Library)

> Track T (Claude Code, `feat/tests`). Против `00-CONTRACT.md` §3.1/§4/§7.5. **Владеет:** `web/vitest.config.ts`,
> **Исполнение:** bounded ClinePass package; role `worker`; route category `code`; exact route/model only from `tools/clinepass-mcp/models.env` — детерминированная логика/вёрстка против контракта; гейт = секция Check.
> `web/src/test/**`, `web/src/**/*.test.tsx`. Запускается после d2/f2/f4 (и далее по мере f5–f13).
> Не редактирует продуктовые компоненты — при баге заводит дефект треку D/F.

## Цель
Покрыть презентационную логику и api-клиент быстрыми компонентными тестами (jsdom, без бэкенда).

## Состав

`web/vitest.config.ts` + `web/src/test/setup.ts` (jsdom, RTL matchers). Dev-deps: `vitest`,
`@testing-library/react`, `@testing-library/jest-dom`, `jsdom` (в `web/package.json` через d/f — если нет,
добавить в devDependencies здесь).

`web/src/components/ui/*.test.tsx` (d2):
- `SeverityBadge`: `medium→warning`(жёлтый), `low→ok`(зелёный), `critical/high` корректные классы.
- `ScoreBar`: градиентная заливка, значение tabular-nums.
- `VideoPlayer`: пустое состояние «Видео недоступно» при пустом `src`; `onTimeUpdate` вызывается; `seekTo` перематывает.
- `TelemetryChart`: принимает `data: TelemetryPoint[]` и `playheadOffset` (рендер без ошибок).
- `DataTable`: сортировка/выбор строки.

`web/src/api/client.test.ts` (f2):
- При `VITE_USE_FIXTURES=true` методы (`listIncidents`, `getIncident`, `queryReport`, `getTickets`…) отдают фикстуры без сети.
- Типы согласованы с §3.1/§7.5 (компилируется + рантайм-форма).

`web/src/pages/*.test.tsx` (f4 + ключевые экраны):
- `IncidentCard`: кейс «нет видео» → placeholder + «Запросить архив»; sync — `playheadOffset` обновляется на `onTimeUpdate`.
- `Report`: дашборд В-1 рендерит KPI и таблицу; клик по нарушению открывает видео-панель.
- `Monitor`: хелпер дедупликации — из списка алярмов один маркер на `unit_id`.

## Check
- `cd web && npx vitest run` зелёный; `npm run typecheck` без ошибок.
- Тест дедупликации монитора доказывает «1 unit_id = 1 маркер».
- Тест `SeverityBadge` доказывает маппинг `medium→warning`, `low→ok`.

## Коммит (обязательно)

Заверши промпт коммитом в свою ветку — **merge на барьере берёт только коммиты**; незакоммиченная
работа в worktree на барьер не попадёт:

```bash
git add -A && git commit -m "t3: <что сделано>"
```
