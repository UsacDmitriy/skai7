# РЭБ-зоны: детекция аномалий и отображение на карте

**Дата:** 2026-06-19  
**Статус:** approved  
**Ветка:** integration

---

## 1. Цель

Переработать РЭБ-зоны: вместо примитивного DBSCAN с константным `avg_risk=50.0` и меткой `GPS_LOSS` — полноценная детекция аномалий телеметрии с оценкой достоверности (confidence score), отображением всех затронутых ТС на карте, пунктирным возможным маршрутом в зоне потери и детальным попапом по каждому ТС.

---

## 2. Контекст: что уже есть

- `api/services/reb_service.py` — восстановление трека одного ТС (gap-периоды + GPS + видео) → не трогается
- `api/services/zones_service.py` — DBSCAN по gap-точкам с `avg_risk=50.0` константой → не трогается
- `web/src/pages/RebRecovery.tsx` — детальный экран одного ТС → не трогается
- `web/src/pages/NavProblemList.tsx` → не трогается
- `web/src/components/ai/RiskHeatLayer.tsx` → не трогается

---

## 3. Архитектура (Подход B)

```
reb_anomaly_service.py
  detect_anomalies(db) → list[RebAnomalyZone]
  ├── _load_gap_periods()
  ├── _load_speed_spikes()      (speed_kmh > 150)
  ├── _load_coord_jumps()       (implied_speed > 300 km/h)
  └── _score_and_cluster()      → DBSCAN + confidence

api/domain/entities.py  (+3 Pydantic-модели)
api/routers/reb.py  (+1 endpoint: GET /api/reb/anomalies)

web/src/components/reb/RebAnomalyLayer.tsx  (новый)
web/src/api/types.ts  (+3 типа)
web/src/api/client.ts  (+getRebAnomalies)
web/src/pages/Monitor.tsx  (добавить <RebAnomalyLayer>)
```

---

## 4. Детекция аномалий

### 4.1 Сигналы (три типа)

**gap** — `period_type = 3` в `navigation__track_periods`. Координаты берутся из `navigation__track_points` в том же `period_index` (если есть) или из соседних периодов.

**speed_spike** — точки `navigation__track_points` с `speed_kmh > 150`. Физически невозможно на дороге; при РЭБ-подавлении GPS вычисляет скорость из мгновенно «перепрыгнувших» координат.

**coord_jump** — две последовательные точки одного ТС (одна дата, соседние `period_index`, соседние `timestamp`), где `haversine(p1, p2) / Δt_sec * 3.6 > 300 км/ч`. Физически невозможное перемещение.

**possible_route** для каждого типа:
- `gap`: берём до 10 GPS-точек из предыдущего видимого периода (period_index-1) и до 10 из следующего (period_index+1), отсортированных по timestamp. Итог: пунктир от последней известной точки до первой после разрыва.
- `speed_spike` и `coord_jump`: `possible_route = []` — пунктир не рисуется (нет разрыва трека).

### 4.2 Confidence score

```python
score = 0

score += 40  # если ≥2 ТС с аномалией в радиусе 5 км в окне ±30 мин
score += 20  # если coord_jump implied_speed > 300 км/ч
score += 20  # если одометр растёт при period_type=3 (distance_odometer_km > 0)
score += 15  # если speed_kmh > 200
score += 10  # если зона встречается на ≥2 разных датах
score += 10  # если gap_duration > 300 сек
score -= 25  # если только 1 ТС и нет gap (только скачки скорости)
score -= 15  # если gap_duration < 30 сек
score -= 10  # если speed_spike единственный и изолированный (1 точка у 1 ТС)
```

**Отображение:**
- `score ≥ 40` → РЭБ-зона, красный круг
- `score 20–39` → Подозрительная аномалия, оранжевый круг
- `score < 20` → шум, не возвращается в API

### 4.3 Кластеризация

DBSCAN с теми же параметрами что в `zones_service.py`:
- `eps = 5000 / 6_371_000` радиан (≈5 км)
- `min_samples = 2`
- `metric = 'haversine'`

Входные точки: объединение всех трёх типов аномалий (gap + speed_spike + coord_jump), каждая несёт `vehicle_plate`, `anomaly_type`, `speed_kmh`, `lat`, `lon`, `ts`.

---

## 5. Новые Pydantic-модели (entities.py)

```python
class AnomalyType(str, Enum):
    gap = "gap"
    speed_spike = "speed_spike"
    coord_jump = "coord_jump"

class VehicleAnomaly(BaseModel):
    vehicle_plate: str
    anomaly_type: AnomalyType
    max_speed_kmh: float | None       # None для gap без точек скорости
    lat: float
    lon: float
    ts_start: str                     # ISO
    ts_end: str | None
    possible_route: list[list[float]] # [[lat,lon], ...] — точки пунктира
    reb_link_id: str | None           # для кнопки /reb/:id

class RebAnomalyZone(BaseModel):
    zone_id: str                      # "reb_anomaly_0", "reb_anomaly_1", ...
    centroid: list[float]             # [lat, lon]
    radius_m: float
    confidence: int                   # итоговый score
    confidence_label: str             # "reb" | "suspicious"
    vehicles: list[VehicleAnomaly]
    event_count: int                  # всего аномальных событий в зоне
    date_count: int                   # кол-во уникальных дат
```

---

## 6. Endpoint

```
GET /api/reb/anomalies
→ 200: list[RebAnomalyZone]   (пустой список если нет данных)
```

Нет параметров. Детерминированный ответ. Добавляется в `api/routers/reb.py`.

---

## 7. Frontend: RebAnomalyLayer.tsx

**Место:** `web/src/components/reb/RebAnomalyLayer.tsx`

**Что рендерит внутри `<MapView>`:**

1. **Circle per zone** — Leaflet `Circle` с `radius=zone.radius_m`, цвет по `confidence_label`:
   - `reb` → `#dc2626` (красный, opacity 0.15 fill, opacity 0.6 stroke)
   - `suspicious` → `#ea580c` (оранжевый, opacity 0.1 fill, opacity 0.5 stroke)

2. **Vehicle markers** — `Marker` на `[anomaly.lat, anomaly.lon]` для каждого ТС в зоне. Иконка: `RadioTower` (как в RebRecovery шапке).

3. **Dashed polyline (possible route)** — `Polyline` по `anomaly.possible_route` с `dashArray: '6 8'`, цвет `#dc2626`, opacity 0.7. Рендерится только если `possible_route.length >= 2`.

4. **Popup per vehicle marker** — открывается по клику:
   ```
   ТС: А 230 КУ 550
   Тип: Потеря GPS / Скачок скорости / Прыжок координат
   Макс. скорость: 247 км/ч
   Confidence: 75 (РЭБ-зона)
   Время: 14:32 – 14:45
   [Открыть РЭБ] → /reb/:reb_link_id  (disabled если null)
   ```
   Использует Leaflet `Popup`, стилизован под существующий дизайн (`bg-bg`, `text-ink`, `text-muted`).

**Интеграция в Monitor.tsx:** Рядом с существующим `<RiskHeatLayer>` добавляется `<RebAnomalyLayer>`, управляемый отдельным тогглом на тулбаре монитора («РЭБ-зоны»).

---

## 8. Тесты

- `api/tests/test_reb_anomaly_service.py` — unit-тесты scoring с mock-данными (gap, speed_spike, coord_jump, multi-vehicle, single-vehicle)
- `api/tests/test_reb_api.py` — интеграционный тест `GET /api/reb/anomalies` возвращает список (может быть пустым)
- `web/src/components/reb/RebAnomalyLayer.test.tsx` — рендер с пустыми зонами, с зоной + 2 ТС, попап открывается

---

## 9. Что не меняется

- `zones_service.py` и `RiskHeatLayer.tsx` — существующий тепловой слой остаётся
- `reb_service.py` и `RebRecovery.tsx` — детальный экран одного ТС
- `NavProblemList.tsx`
- DuckDB schema — только читаем существующие таблицы

---

## 10. Новые файлы

| Файл | Тип |
|------|-----|
| `api/services/reb_anomaly_service.py` | новый |
| `web/src/components/reb/RebAnomalyLayer.tsx` | новый |
| `web/src/components/reb/RebAnomalyLayer.test.tsx` | новый |
| `api/tests/test_reb_anomaly_service.py` | новый |

## Измененные файлы

| Файл | Изменение |
|------|-----------|
| `api/domain/entities.py` | +3 Pydantic-модели |
| `api/routers/reb.py` | +1 endpoint |
| `web/src/api/types.ts` | +3 типа |
| `web/src/api/client.ts` | +getRebAnomalies() |
| `web/src/pages/Monitor.tsx` | +<RebAnomalyLayer> + тоггл |
