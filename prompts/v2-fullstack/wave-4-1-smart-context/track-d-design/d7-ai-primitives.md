# d7 · AI-примитивы (идеи #11/#12/#14)

> Трек **Design**. Против `00-CONTRACT.md` §4/§8.4 + токены d1. **Владеет:** `web/src/components/ai/*`.
> **Модель:** 🔵 Sonnet — презентационные компоненты против контракта; гейт = typecheck/Storybook.
> **Волна 4.1**, окно 2 (web). Параллельно с backend (кодит против §8.4 типов и фикстур).

## Цель

Переиспользуемые презентационные компоненты AI-слоя (props → разметка, без бизнес-логики/fetch),
на которых f15/f16/f18 соберут экраны.

## Компоненты (один файл на компонент, `web/src/components/ai/`)

1. **`SceneContextChip.tsx`** — props `SceneContext` (§8.4): иконка погоды + день/ночь + покрытие;
   цвет по риску (мокро/гололёд — предупреждающий). Компактный чип для карточки.
2. **`DiscrepancyBadge.tsx`** — props `WeatherCrossCheck`: при `discrepancy=true` — бейдж
   «⚠ Камера ↔ погода» с тултипом (что не сошлось: `discrepancy_kind`); при `false` — ничего.
3. **`ForecastSparkline.tsx`** — props `RiskForecast.trend`: мини-спарклайн прогноза 7д с
   доверительным коридором (`ci_low/ci_high`) и точкой аномалии; `tabular-nums`.
4. **`RiskHeatLayer.tsx`** — обёртка `leaflet.heat` (или совместимая): props `RiskZone[]` → тепловой
   слой по `centroid`+`avg_risk`; тоггл `kind` (incident/reb). Только слой, без логики карты (её даёт d4/f6).

## Требования

- TS, строгие props из типов §8.4; именованный экспорт; иконки `lucide-react`; токены d1 (без хардкод-hex).
- Пустые/`unknown` состояния не падают (нет данных → нейтральный вид).

## Check

- Все 4 файла компилируются (`tsc --noEmit`).
- `SceneContextChip` рендерит погоду/день-ночь; `DiscrepancyBadge` показывается только при `discrepancy`.
- `ForecastSparkline` рисует коридор и аномалию; `RiskHeatLayer` принимает `RiskZone[]` и тоггл `kind`.

## Коммит (обязательно)

Заверши промпт коммитом в свою ветку — **merge на барьере берёт только коммиты**:

```bash
git add -A && git commit -m "d7: <что сделано>"
```
