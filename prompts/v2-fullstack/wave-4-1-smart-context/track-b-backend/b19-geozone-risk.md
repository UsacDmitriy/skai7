# b19 · Geozone risk — кластеры + РЭБ-зоны (идея #14)

> Трек **Backend/Data**. Против `00-CONTRACT.md` §8.1/§8.3/§8.4. **Владеет:** `api/services/zones_service.py`,
> `api/sql/32_v_risk_zones.sql`, роутер `api/routers/zones.py` (в `ALL_ROUTERS`).
> **Модель:** 🔴 Opus — пространственная кластеризация + агрегация двух источников.
> **Волна 4.1**, окно 1 (backend). Зависит от: b3 (`v_incidents` lat/lon/risk), навигация (`period_type=3`).

## Цель

Выявить зоны риска: кластеры алярмов (`kind=incident`) и зоны GPS-jamming (`kind=reb`) с прогнозом по
часу суток. `GET /api/zones?kind=&hour=` → `RiskZone[]` (§8.4). Питает тепловую карту f18.

## Состав

- `zones_service.compute_zones() -> list[RiskZone]`:
  - **DBSCAN** (sklearn, haversine-метрика) по `lat/lon` из `v_incidents` → центроид, радиус,
    `alarm_count`, `avg_risk`, `top_alarm_code`, `peak_hour` (мода часа `ts`). `kind='incident'`.
  - РЭБ-зоны: кластеры точек `navigation__track_periods` `period_type=3` → `kind='reb'`.
- `api/sql/32_v_risk_zones.sql` — материализация/вью при необходимости (или сервис считает на лету и кэширует).
- Роутер `GET /api/zones`: фильтры `kind` (`incident|reb`), `hour` (0..23, по `peak_hour`); пустой результат → `[]`.

## Зависимости

`scikit-learn` (общий с b18). Детерминизм DBSCAN: фиксированные `eps`/`min_samples`, стабильная сортировка
зон по `zone_id`. Без `random`.

## Check

- `GET /api/zones` → 200 `RiskZone[]`; есть и `kind=incident`, и `kind=reb`.
- `?kind=reb` отдаёт только РЭБ-зоны; `?hour=22` фильтрует по `peak_hour`.
- Кластеры детерминированы между прогонами; `radius_m`>0, `avg_risk ∈ [0,100]`.
- Нет подходящих точек → `[]` (не ошибка).

## Коммит (обязательно)

Заверши промпт коммитом в свою ветку — **merge на барьере берёт только коммиты**:

```bash
git add -A && git commit -m "b19: <что сделано>"
```
