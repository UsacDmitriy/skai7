# b34 · Единый рейтинг водителя + лидерборд (фича #26, владелец §13.2)

> Трек **Backend/Data**. Против `00-CONTRACT.md` §13.0/§13.2/§13.4. **Владеет:**
> `api/services/driver_score_service.py`, `api/domain/driver_score.py`, роутер
> `api/routers/driver_score.py` (автодискавери — НЕ редактируй `api/routers/__init__.py`).
> **Исполнение:** bounded ClinePass package; role `worker`; route category `code`; exact route/model only from `tools/clinepass-mcp/models.env` — бленд по зафиксированной формуле; гейт = Check + tu-score.
> **Волна 5.3**, окно 1, **после b33** (вызывает его сервис). Зависит от: b33, incidents_service
> (готовый `risk_score` инцидентов — §2 не пересчитывать).

## Цель

`GET /api/driver-score` (лидерборд всех водителей) и `GET /api/driver-score/{plate}` —
единый рейтинг 0..100, блендящий риск (§2) и позитив (§13.1): сравнение водителей становится
честным (видео+телематика в одном числе), KPI-запрос всех трёх клиентов.

## Состав

- `driver_score_service` — формулы **дословно §13.2** (урок b27: компоненты float, округление
  ОДИН раз в конце):
  - `avg_risk_score` = средний `risk_score` алармов ТС **из готовых данных инцидентов**
    (incidents_service / `v_incidents` — формулу §2 НЕ пересчитывать и НЕ копировать);
    нет алармов → `0.0`;
  - `positive_score` — **вызов сервиса b33** (`positive_score_service.score(plate)`), не дублирование;
  - `risk_component = 0.6·(100 − avg_risk_score)` (float); `positive_component = 0.4·positive_score` (float);
  - `unified_score = clamp(round(risk_component + positive_component), 0, 100)`;
  - `leaderboard()` — ВСЕ ТС из `driver_reference` (включая без алармов), сортировка
    `unified_score` desc, tie-break `vehicle_plate` asc (стабильность);
  - `score(plate)`; неизвестный plate → 404.
- `api/domain/driver_score.py` — Pydantic `DriverScore` **дословно §13.2** (включая обе компоненты
  и `avg_risk_score`/`positive_score`/`green_zone` — прозрачность бленда).
- Роутеры `GET /api/driver-score`, `GET /api/driver-score/{plate}` — модульный `router`.

Пример элемента лидерборда (формат — ровно такой):

```json
{ "vehicle_plate": "A079AM250", "driver_id": "DRV-4459", "driver_name": "Михайлов Антон Борисович",
  "unified_score": 78, "risk_component": 42.6, "positive_component": 35.2,
  "avg_risk_score": 29.0, "positive_score": 88, "green_zone": false }
```

## Check

- `curl -s localhost:8000/api/driver-score | jq -e 'length>0'` — строк == числу ТС в
  `driver_reference` (не хардкод); сортировка desc подтверждена:
  `jq -e '[.[].unified_score]|. == (sort|reverse)'`.
- Инвариант бленда на каждом элементе:
  `jq -e '.[]|((.risk_component+.positive_component)|round|if .>100 then 100 elif .<0 then 0 else . end) == .unified_score'`.
- ТС без алармов: `avg_risk_score==0.0`, `unified_score` высокий (200, не NaN).
- 404 на `__nope__`; `curl -s localhost:8000/openapi.json | jq -e '.paths."/api/driver-score"'`.
- `grep -n "risk_score" api/services/driver_score_service.py` — данные из incidents, формула §2
  не скопирована; `grep -n "positive_score_service" ...` — вызов b33.
- Детерминизм: два вызова → идентично (включая порядок). `pytest api/tests/unit -q` зелёный.

## Коммит (обязательно)

Заверши промпт коммитом в свою ветку — **merge на барьере берёт только коммиты**:

```bash
# стейджи только свои файлы (НЕ git add -A)
git add api/services/driver_score_service.py api/routers/driver_score.py api/domain/driver_score.py
git commit -m "b34: единый рейтинг водителя + лидерборд — /api/driver-score (§13.2)"
```
