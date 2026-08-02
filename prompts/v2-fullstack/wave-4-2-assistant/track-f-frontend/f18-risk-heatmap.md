# f18 · Risk heatmap + зоны на мониторе (идея #14)

> Трек **Frontend**. Против `00-CONTRACT.md` §8.3/§8.4. **Владеет:** **аддитивная** правка
> `web/src/pages/Monitor.tsx`; использует d7 (`RiskHeatLayer`), `web/src/components/map/`, f2-клиент.
> **Исполнение:** owner-only gate — Claude/Codex; ClinePass excluded from shared contracts, integration, deterministic acceptance, and commit — интерактив карты + производительность + кросс-слой фильтры.
> **Волна 4.2**, окно 2 (web). Зависит от: d4/f6 (карта), d7 (`RiskHeatLayer`), `GET /api/zones` (b19).

## Цель

Наложить на «Монитор» **тепловую карту нарушений** и слой **зон риска** (`v_risk_zones`), с фильтрами
тип/время/роль. Никто из конкурентов не даёт РЭБ-зоны — показать `kind=reb` отдельным слоем.

## Состав

- f2-клиент: `getZones({kind?, hour?}) → RiskZone[]` (§8.4).
- В `Monitor.tsx` (аддитивно): тоггл слоёв «Тепловая карта» / «Зоны инцидентов» / «РЭБ-зоны»;
  `RiskHeatLayer` по `centroid`+`avg_risk`; попап зоны (`top_alarm_code`, `peak_hour`, `alarm_count`).
- Фильтры: по часу суткок (`peak_hour`), по роли (Логист — без DMS-зон); виртуализация/throttle при многих точках.
- Состояния loading/empty/error; пустые зоны → слой пуст, карта работает.

## Check

- На «Мониторе» включается тепловой слой и слой зон; РЭБ-зоны отдельным тоглом; попап зоны корректен.
- Фильтр по часу/роли согласован; много точек — без лагов (throttle). На фикстурах без сети.
- Регрессий по f6 (Monitor) нет; `npm run typecheck` зелёный.

## Коммит (обязательно)

Заверши промпт коммитом в свою ветку — **merge на барьере берёт только коммиты**:

```bash
# параллельно в одном worktree — стейджи только свои файлы (НЕ git add -A)
git add web/src/pages/Monitor.tsx
git commit -m "f18: <что сделано>"
```
