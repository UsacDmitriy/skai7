# b30 · Review Queue — сервис очереди верификации (фича #23, владелец §11.1)

> Трек **Backend/Data**. Против `00-CONTRACT.md` §11.0–§11.2, §11.4. **Владеет:**
> `api/services/review_service.py`, `api/domain/review.py`, роутер `api/routers/review.py`
> (автодискавери `api/main.py:_discover_routers` — НЕ редактируй общий `api/routers/__init__.py`),
> журнал `output/review_queue.csv`. **Исполнение:** bounded ClinePass package; role `worker`; route category `code`; exact route/model only from `tools/clinepass-mcp/models.env` — журнальная статусная модель против
> контракта; гейт = Check + tu-review. **Волна 5.1**, окно 1 (backend).
> Зависит от: v_incidents (b3), `consistency_service.report()` → `evidence_rate` (b28), эмиттер b25.

## Цель

`GET /api/review-queue` + `POST /api/review-queue/{incident_id}` (§11.1): каждый инцидент получает
статус ревью `pending|validated|dismissed` с журналом решений — workflow Фомина «подтверждено видео
5 из 39» вместо разовой кнопки.

## Состав

- **Журнал** `output/review_queue.csv` — зеркало паттерна `actions_service` (`_actions_csv_path`,
  `_ensure_csv`): путь `settings.output_dir / "review_queue.csv"`, колонки
  `decided_at,incident_id,decision,note`; `decided_at` пишет сервер при записи (прецедент
  `actions_service.record`); append-only.
- `review_service`:
  - `queue(status?) -> ReviewQueue`: все инциденты из `v_incidents` (id, alarm_code, severity,
    vehicle_plate, ts, video_available) + статус из журнала (**последняя** запись по incident_id
    побеждает; нет записи → `pending`); фильтр по статусу; `counts` по всем (не по фильтру);
    `evidence_rate` — из `consistency_service.report()` (b28, не пересчитывать);
  - `decide(incident_id, decision, note?) -> ReviewItem`: валидация инцидента (404 если нет в
    `v_incidents`), запись строки в журнал, эмит `review_decision` в `ai_metric_events` через
    эмиттер b25 (исключение/выключен → тихий no-op, решение уже записано);
  - битая строка журнала (мало колонок/мусор) → пропустить (§11.4), не 5xx;
  - `reset_state()` для тестов (прецедент `actions_service.reset_overrides`).
- `api/domain/review.py` — Pydantic `ReviewItem`/`ReviewQueue` **дословно по §11.2**.
- Роутер: `GET /api/review-queue?status=`, `POST /api/review-queue/{incident_id}`
  (body `{decision, note?}`; неизвестный `decision` → 422 — Literal в Pydantic).
- **НЕ трогать** `actions_service`/`actions.csv` (§11.0: единый словарь, без дублей статуса).

Пример ответа `GET /api/review-queue?status=pending` (формат — ровно такой):

```json
{
  "items": [
    { "incident_id": "12345", "alarm_code": "DMS_DROWSY", "severity": "critical",
      "vehicle_plate": "T780РН198", "ts": "2026-05-14T08:12:00Z", "video_available": true,
      "status": "pending", "note": null, "decided_at": null }
  ],
  "counts": { "pending": 53, "validated": 1, "dismissed": 1 },
  "evidence_rate": 0.98
}
```

## Check

- `curl -s localhost:8000/api/review-queue | jq -e '.items|length>0'`; сумма `counts` == числу
  инцидентов в `v_incidents` (не хардкод).
- `curl -s -X POST localhost:8000/api/review-queue/<id> -H 'content-type: application/json' \
  -d '{"decision":"validated","note":"видео подтверждает"}' | jq -e '.status=="validated"'` —
  и строка появилась в `output/review_queue.csv`.
- Повторный POST с `dismissed` по тому же id → статус перезаписан, в `counts` инцидент один раз.
- 404 на `__nope__`; 422 на `{"decision":"maybe"}`.
- Пустой/отсутствующий журнал → все `pending` (200); журнал с битой строкой → строка пропущена.
- `curl -s localhost:8000/openapi.json | jq -e '.paths."/api/review-queue"'` — роутер подхвачен
  автодискавери (модульный `router`; иначе тихий 404 — прецедент scene).
- `pytest api/tests/unit -q` зелёный (регресс не сломан); `actions.csv` не изменился.

## Коммит (обязательно)

Заверши промпт коммитом в свою ветку — **merge на барьере берёт только коммиты**:

```bash
# стейджи только свои файлы (НЕ git add -A)
git add api/services/review_service.py api/routers/review.py api/domain/review.py
git commit -m "b30: review queue — статусная модель + журнал + /api/review-queue (§11)"
```
