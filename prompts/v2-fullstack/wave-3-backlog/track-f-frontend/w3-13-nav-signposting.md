# W3-13 · Навигация: реальные роуты + честный «ComingSoon» вместо пустого 404

> Волна 3 · бэклог. Трек **Frontend** (владелец f1 — роутинг/оболочка). Против `00-CONTRACT.md` **§9.4**.
> **Модель:** 🔵 Sonnet — детерминированная маршрутизация/вёрстка; гейт = секция Check.
> **Владеет:** `web/src/App.tsx` (роуты + NAV + catch-all), `web/src/components/.../ComingSoon.tsx` (новый).
> **Зависит от** w3-11 (страницы хаба). **Не блокирует** P0/P1/P2.

## Контекст (мёртвая навигация)

В боковом меню ~10 пунктов ведут на generic `Placeholder` «Раздел в разработке» (catch-all `App.tsx` ~стр.269) —
ощущение пустого 404. Решение (по согласованию): **не удалять**, а честно подписать «скоро / Волна 4 (AI)».
Плюс новые рабочие экраны Волны 3 нужно подключить роутами.

## Что сделать

1. **Реальные роуты** (внутри `AppShell`, до catch-all, рядом с существующими `/trip/:id`, `/reb/:id`):
   `/fleet-health` → `FleetHealth`, `/fleet-health/fuel/:plate` → `FuelCard`,
   `/fleet-health/sensors/:plate` → `SensorCard`, `/navigation` → `NavProblemList` (lazy + Suspense, как остальные).
   После добавления `/fleet-health` пункт «Здоровье парка» (NAV, ~стр.71) перестаёт падать в catch-all.
2. **Компонент `ComingSoon.tsx`**: принимает `{ title, description, wave }`; рендерит название секции +
   одну строку описания + пилюлю «Скоро · Волна N». Заменяет generic `Placeholder` в catch-all через
   карту `path → {title, description, wave}` (см. §9.4):
   - `/safety` → «Мониторинг безопасности · агрегированные KPI — Волна 4».
   - `/live`,`/archive`,`/downloads` → «Видеопоток/архив/загрузки — Волна 4 (стриминг)».
   - `/validation`,`/response` → «Блоки валидации и реагирования — Волна 4 (workflow)».
   - `/dashboards`,`/quick-report` → «Расширенная BI-аналитика — Волна 4 (AI-копилот, §8)».
   `Placeholder` оставить **только** как Suspense-фолбэк («Загрузка…»).
3. **NAV-бейджи** (`NAV`, ~стр.41–73): на «мёртвых» пунктах — бейдж `W4` (честно). Заменить «NEW» у
   `/quick-report` на `W4`. Рабочие пункты (`/monitor`,`/events`/`/`,`/tickets`,`/report`,`/fleet-health`) — без бейджа.
   Опц.: добавить пункт «Навигация (РЭБ)» → `/navigation` в группе «Парк».

## Check

- `/fleet-health`, `/fleet-health/fuel/:plate`, `/fleet-health/sensors/:plate`, `/navigation` рендерят
  реальные экраны (w3-11), не catch-all.
- Любой «мёртвый» путь (напр. `/live`) рендерит `ComingSoon` с **описанием секции** и пилюлей «Скоро · Волна 4»,
  а **не** generic «Раздел в разработке».
- NAV: мёртвые пункты несут бейдж `W4`; «NEW» у `/quick-report` заменён; рабочие пункты без бейджа.
- `App.tsx` больше не отправляет `/fleet-health` в generic placeholder; `npm run typecheck` зелёный; a11y NAV (aria-current).

## Коммит (обязательно)

```bash
git add -A && git commit -m "w3-13: роуты fleet-health/navigation + ComingSoon (Волна 4) вместо пустого 404"
```
