# W3-11 · Экраны «Здоровье парка» (хаб + карточки fuel/sensors + список навигации)

> Волна 3 · бэклог. Трек **Frontend**. Против `00-CONTRACT.md` **§9** (§9.0/§9.4) + §7.8-стиль состояний.
> **Модель:** 🔵 Sonnet — детерминированная вёрстка против контракта; гейт = секция Check.
> **Владеет:** `web/src/pages/FleetHealth.tsx`, `FuelCard.tsx`, `SensorCard.tsx`, `NavProblemList.tsx`.
> Использует UI-примитивы d2 (`@/components`, `DataTable`/`Card`/бейджи) и API-клиент w3-10. **Зависит от** w3-10.
> Маршруты подключает w3-13. **Не блокирует** P0/P1/P2.

## Контекст (disjoint — §9.0)

Домены почти не пересекаются (fuel:10, sensors:7, nav:5, объединение 17, в видеопарке 2). Экраны должны
честно показывать «—» там, где у ТС нет домена, и баннер покрытия — это фича, не баг.

## Экраны (все на живом API и фикстурах `VITE_USE_FIXTURES=true`; loading/empty/error; a11y таблиц)

1. **`FleetHealth.tsx` — хаб-ростер** (`/fleet-health`). Данные: `client.getFleetHealth()`.
   - **Баннер покрытия** сверху: «Топливо: 10 ТС · Сенсоры: 7 ТС · Навигация: 5 ТС · в видеопарке: 2».
   - **Таблица** (`DataTable`): ТС (+бейдж «в видеопарке» для 2 строк) · Топливо Δ ЗИС−карта (severity-цвет
     при >4 л; «—» если нет) · Пробег CAN−GPS («—» если нет) · Сенсоры online (точка online/stale/offline; «—») ·
     Навигация (gap-бейдж → `/reb/:reb_link_id`; «—»). Клик по строке → самый «богатый» домен ТС:
     fuel-карточка → иначе sensor-карточка → иначе `/reb/:id`.
2. **`FuelCard.tsx`** (`/fleet-health/fuel/:plate`). `client.getFuel(plate)`: шапка KPI
   (`volume_delta_zis_minus_card_l`, `recon_status`-бейдж), таблица сверки (`FuelReconRow[]`),
   список заправок (`FuelEvent[]`). Пустые списки → дружелюбная плашка, не ошибка. 404 → «ТС не найдено».
3. **`SensorCard.tsx`** (`/fleet-health/sensors/:plate`). `client.getSensors(plate)`: KPI CAN−GPS,
   **спарклайн** из `daily_mileage` (7 точек), блоки engine/fuel_level/snapshot. `online_status="stale"` →
   нейтральный бейдж (не ошибка). `distance_gap…=null` → «нет данных».
4. **`NavProblemList.tsx`** (`/navigation`). `client.listNavProblems()`: карточки/строки с
   `problem_description`, gap-статами; кнопка «Открыть РЭБ» → `/reb/:reb_link_id`. unmatched-ТС
   (`reb_link_id=null`) — показан, но кнопка disabled.

## Check

- `/fleet-health` рендерит 17 строк (живой API) / фикстуры; баннер покрытия отображает 10/7/5/2.
- Ячейки отсутствующих доменов — «—» (не пусто/не ошибка); 2 строки помечены «в видеопарке».
- Клик по строке ведёт в правильный домен; gap-бейдж/кнопка РЭБ ведёт в `/reb/:id` (matched), disabled у unmatched.
- `FuelCard`/`SensorCard` рендерят сверку/спарклайн; 404 (неизв. ТС) → плашка «не найдено», не белый экран.
- `SensorCard` **не** запрашивает/не показывает сырые graph_points.
- Состояния loading/empty/error у всех экранов; `npm run typecheck` зелёный.

## Коммит (обязательно)

```bash
git add -A && git commit -m "w3-11: экраны Здоровье парка (хаб + fuel/sensor карточки + список навигации)"
```
