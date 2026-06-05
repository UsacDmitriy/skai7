# b18 · Risk forecast + рекомендации (идея #12)

> Трек **Backend/Data**. Против `00-CONTRACT.md` §8.3/§8.4. **Владеет:** `api/services/forecast_service.py`,
> роутер `api/routers/forecast.py` (в `ALL_ROUTERS`).
> **Модель:** 🔴 Opus — алгоритм прогноза/аномалий + генерация рекомендаций.
> **Волна 4.1**, окно 1 (backend). Зависит от: enrichment (`events_last_7d`), история алярмов по plate.

## Цель

`GET /api/reports/forecast/{plate}` → `RiskForecast` (§8.4): тренд-прогноз нарушений на 7 дней,
флаг аномалии и **предписывающие рекомендации**.

## Состав

- `forecast_service.forecast(plate) -> RiskForecast`:
  - Ряд дневных счётчиков алярмов водителя за доступный период (детерминированно из БД).
  - **ARIMA** (statsmodels) → `trend[]` `{date, predicted_events, ci_low, ci_high}` на 7 дней;
    при недостатке точек — наивный baseline (скользящее среднее), без падения.
  - **IsolationForest** (sklearn) по фичам `[daily_count, max_speed, night_share, harsh_share]` →
    `anomaly: bool` + `anomaly_reason` (какая фича выбила).
  - `recommendations: string[]` — детерминированные правила (напр. «2 из 3 событий ночью → коучинг по
    утренней бдительности», «рост резких торможений → дистанция»); опц. усиление нарративом b22.
- Роутер `GET /api/reports/forecast/{plate}`; неизвестный plate → 404; пустая история → валидный
  `RiskForecast` с нулевым трендом и `anomaly=false` (не падать).

## Зависимости

`statsmodels`, `scikit-learn` в `api/requirements.txt`. Детерминизм: фиксированный `random_state`,
без `datetime.now()` (опорная дата — максимум из данных).

## Check

- `GET /api/reports/forecast/{plate}` (существующий) → 200 `RiskForecast`; `trend` длиной 7, `ci_low ≤ predicted ≤ ci_high`.
- Водитель с историей ночных событий → `recommendations` непуст и релевантен; аномальный всплеск → `anomaly=true`.
- Неизвестный plate → 404; пустая история → валидный пустой прогноз без исключения.
- Повторные вызовы детерминированы (один вход → один выход).

## Коммит (обязательно)

Заверши промпт коммитом в свою ветку — **merge на барьере берёт только коммиты**:

```bash
git add -A && git commit -m "b18: <что сделано>"
```
