# f23 · Триггер Dispatch Alert: точка входа в `/alert/:id` из ленты (идея #5)

> Трек **Frontend**. **Волна 4.3 (Ops & Trust)** · достройка идеи #5 (целостность экранов).
> Против `00-CONTRACT.md` §3.1 (`alarm_type_catalog.auto_request_video`), §7.5 (`DispatchAlert`), §7.8 (AC «Dispatch alert»).
> **Модель:** 🔵 Sonnet — точечная навигация + overlay-паттерн; гейт = typecheck, без бизнес-логики модала.
> **Владеет:** правкой `web/src/pages/EventsFeed.tsx` (+ опционально `web/src/pages/Monitor.tsx`). Зависит от f9 (`DispatchAlert.tsx`, маршрут `/alert/:id` в `App.tsx` уже есть).

## Контекст (зачем)

`DispatchAlert.tsx` (f9) — overlay-модал на `/alert/:id` (идея #5 «push-alert»: при критическом алярме с
`auto_request_video=true` диспетчер получает немедленный алерт поверх рабочего экрана). **Но ни один экран
на `/alert/:id` не ведёт** — маршрут достижим только ручным вводом URL. Идея #5 в UI не запускается.
Этот промпт **только добавляет точку входа** — логику модала не трогает и не дублирует.

## Цель

Из `EventsFeed` (и опционально `Monitor`) дать диспетчеру открыть `/alert/:id` **как overlay поверх
текущего экрана** для алярмов-кандидатов на push (критический + `auto_request_video=true`).

## Состав

1. **Overlay-навигация (критично).** В `EventsFeed.tsx` уже есть `useNavigate`; добавить `useLocation`
   из `react-router-dom`. Открытие алерта — **строго** через background-location pattern (см. `App.tsx`
   `AppRoutes`: фон рисует `<Routes location={background ?? location}>`, модал — второй `<Routes>`):
   ```ts
   navigate(`/alert/${id}`, { state: { backgroundLocation: location } })
   ```
   Без `state.backgroundLocation` модал откроется без фона и паттерн ломается (`DispatchAlert.goBackground`
   уйдёт в `navigate('/', {replace:true})` вместо `navigate(-1)`). Это must — зафиксировать комментарием.

2. **Критерий кандидата (точно по контракту).** Push-кандидат — алярм, у которого
   `alarm_type_catalog.auto_request_video === true` (§3.1), как правило `severity === 'critical'`.
   ⚠️ **Поле `auto_request_video` НЕ приходит в `IncidentSummary`** (`web/src/api/types.ts:44` — есть
   `alarm_code`, `severity`, `video_available`, но не `auto_request_video`). Резолвим по `alarm_code`
   локальной картой — **тем же приёмом, что уже применён** в `TripDossier.tsx` (`SEVERITY_BY_CODE:
   Record<string, Severity>`, выведенный из `alarm_code`). Завести рядом с маппингами `EventsFeed`:
   ```ts
   // auto_request_video=true из alarm_type_catalog (data/analysis/alarm_types.json, §3.1).
   const AUTO_VIDEO_CODES = new Set([
     'DMS_DROWSY', 'DMS_PHONE', 'DRIVER_SUBSTITUTION',
     'HARSH_BRAKING', 'ADAS_FCW', 'CAMERA_TAMPER', 'ADAS_PCW',
   ])
   const isPushCandidate = (r: IncidentSummary) =>
     r.severity === 'critical' && AUTO_VIDEO_CODES.has(r.alarm_code)
   ```
   7 кодов — ровно строки `auto_request_video:true` из `alarm_types.json` (источник истины; при расхождении
   синхронизировать по нему). Связку `severity==='critical'` оставить, чтобы push-набор совпадал с идеей #5.

3. **Явная аффорданс (primary).** Для строк-кандидатов — кнопка/иконка «🔴 Алерт» (title «Открыть алерт»)
   в `EventRow`, по аналогии с уже существующей врезкой `/trip/:id` (там `<Link>` + `e.stopPropagation()`
   в `onClick`/`onKeyDown`, чтобы не сработала навигация строки в `/incidents/:id`). Здесь — `<button>` с
   `stopPropagation` и `navigate(..., { state: { backgroundLocation: location } })`. Для не-кандидатов
   кнопку не рендерить (ничего лишнего в строке).

4. **Авто-открытие (optional, guarded).** Допустимо при монтировании автоматически открыть **один**
   верхний push-кандидат — **детерминированно**, без `Date.now()`/random: брать первый по уже готовому
   порядку `visible`/`filtered`. Сделать защищённым (открывать ровно раз за загрузку: ref-флаг; не
   повторять при ре-рендере/смене роли; не открывать, если модал уже открыт — проверять
   `location.state?.backgroundLocation`). Если сомнения в навязчивости — оставить только аффорданс п.3,
   авто-открытие за флагом по умолчанию off. Приоритет — явная кнопка.

5. **Monitor (опционально).** В `Monitor.tsx` (`useNavigate` уже есть) для критического маркера/строки —
   та же кнопка «Алерт» с тем же overlay-вызовом. Только если не раздувает диф; иначе перенести в отдельный
   промпт.

## Check

- **Минимальная приёмка идеи #5 (§7.8 AC) = видимая кнопка-аффорданс п.3 на каждом push-кандидате.**
  Авто-открытие п.4 — НЕ требование AC: строго за локальным флагом (default **off**); включённое —
  детерминированное и однократное (см. п.4).
- Из ленты на строке-кандидате видна аффорданс «🔴 Алерт»; клик открывает `/alert/:id` **поверх** ленты —
  фон (таблица) виден сквозь затемнение и **не размонтируется** (overlay-паттерн `App.tsx` работает).
- Навигация идёт с `state: { backgroundLocation: location }`; закрытие модала (Esc/«Всё в порядке») через
  `DispatchAlert.goBackground` → `navigate(-1)` возвращает на ленту (f9 уже это делает).
- Кнопка не конфликтует с кликом строки: `stopPropagation` на `onClick`/`onKeyDown` (как у врезки `/trip`).
- Кандидат определяется по `severity==='critical' && AUTO_VIDEO_CODES.has(alarm_code)`; у не-кандидатов
  кнопки нет; набор кодов совпадает с `auto_request_video:true` из `data/analysis/alarm_types.json`.
- Авто-открытие (если включено) срабатывает **один раз** на загрузку, детерминированно (без Date.now/random),
  не повторяется при смене роли/ре-рендере и не открывается, когда модал уже на экране.
- Работает на живом API и на фикстурах (`VITE_USE_FIXTURES=true`): `getAlert(id)` резолвит инцидент по id.
- Логика модала не дублирована — добавлена только навигация. `npm run typecheck` зелёный.

## Коммит (обязательно)

Заверши промпт коммитом в свою ветку — **merge на барьере берёт только коммиты**:

```bash
# параллельно в одном worktree — стейджи только свои файлы (НЕ git add -A)
git add web/src/pages/EventsFeed.tsx web/src/pages/Monitor.tsx
git commit -m "f23: точка входа в /alert/:id из ленты (overlay-триггер идеи #5)"
```
