# f21 · Data-quality + AI-метрики панель (по research-отчёту)

> Трек **Frontend**. Против `00-CONTRACT.md` §8.7. **Владеет:** `web/src/pages/Metrics.tsx`,
> `web/src/components/ai/DataQualityPanel.tsx`. Использует d7-примитивы и f2-клиент.
> **Модель:** 🔵 Sonnet — вёрстка/состояния против контракта; гейт = typecheck.
> **Волна 4.3** (AI Ops & Trust), окно 2 (web). Зависит от: `GET /api/metrics/ai`, `GET /api/metrics/data-quality` (b25);
> маршрут `/metrics` + пункт меню — из prep `w3-18`; типы/клиент/фикстуры — из prep `w3-17`.

## Цель

Панель доверия и пользы: качество данных (camera-offline / missing GPS-media / weather-mismatch) и KPI
AI-слоя (recommendation-acceptance / copilot tool-success / zone-hit). Для безопасника/диспетчера/PO.

## Состав

- f2-клиент: `getAiMetrics() → AiMetrics`, `getDataQuality() → DataQuality` (§8.7).
- `DataQualityPanel.tsx` — плитки `*_ratio` со светофором (низкое качество → предупреждение).
- `Metrics.tsx` (маршрут `/metrics`) — KPI AI-слоя + data-quality; пустые данные → empty-state.
- Состояния loading/empty/error; работает на фикстурах (`VITE_USE_FIXTURES`).

## Check

- `/metrics` показывает KPI и data-quality на живом API и фикстурах; `*_ratio` отрисованы как доли.
- Низкое качество данных подсвечено; пустые метрики → empty-state, не падает. `npm run typecheck` зелёный.

## Коммит (обязательно)

Заверши промпт коммитом в свою ветку — **merge на барьере берёт только коммиты**:

```bash
git add -A && git commit -m "f21: <что сделано>"
```
