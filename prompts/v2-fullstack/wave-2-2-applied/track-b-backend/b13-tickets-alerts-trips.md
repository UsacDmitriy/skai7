# b13 · Tickets + Alerts + Trips — сервис и роутеры

> Трек **Backend/Data**. Против `00-CONTRACT.md` §7.4/§7.5 (идеи #5/#6/#7). **Владеет:** `api/services/tickets_service.py`, роутеры `api/routers/tickets.py`, `api/routers/alerts.py`, `api/routers/trips.py`.
> **Модель:** 🔵 Sonnet — детерминированная логика/вёрстка против контракта; гейт = секция Check.
> Кодит против контракта. **Зависит от:** b5 (схемы `IncidentDetail`, `TelemetryPoint`, репозитории/сервис incidents), b6 (паттерн роутеров, `actions_service` пишет `output/actions.csv`). Параллелится с b10/b11/b12. Роутеры включаются в `api/main.py` (x2/b6).

## Цель

Три прикладных среза поверх готового домена incidents:
- **Tickets** (идея #6) — журнал заявок из `output/actions.csv`.
- **Dispatch alert** (идея #5) — карточка инцидента с видео-окном ±15с для немедленной реакции.
- **Trip dossier** (идея #7) — видеодосье поездки: трек + таймлайн событий.

## Сервис `api/services/tickets_service.py`

- `list_tickets(db) -> list[Ticket]` (схема §7.5 `Ticket{id,created_at,incident_id,action,comment,status,deadline,is_overdue}`):
  читать `output/actions.csv` (колонки `created_at,incident_id,action,comment` от `actions_service` b5/b6),
  маппить в `Ticket`; `id` — детерминированно (индекс/`crc32` строки), `status` — дефолт `"active"`
  (единый enum `Status` §3.1, **НЕ** `"new"`; если в CSV нет колонки статуса). `is_overdue = deadline<now И status∉{closed}`;
  `deadline=null` → `is_overdue=false`. Файла нет → пустой список (не ошибка).
- `get_alert(db, id) -> DispatchAlert | None` (схема §7.5): берёт `IncidentDetail` (через incidents-сервис b5),
  оборачивает в `DispatchAlert{incident, video_window_sec=15, requested_at}`; видео ±15с вокруг `ts` —
  ссылки/окно из `cameras`/`cam_*_url` инцидента. `None` если инцидента нет (роутер → 404).
- `get_trip(db, id) -> TripDossier | None` (схема §7.5): `TripDossier{vehicle_plate, track, timeline}`:
  `track: TelemetryPoint[]` — из `track_points` по `id` (как `incidents_service.get_telemetry`);
  `timeline: {ts_offset, alarm_code, label, has_video}[]` — алярмы того же ТС в окне поездки.
  `None` если данных по `id` нет (роутер → 404).

## Роутеры (паттерн b6: `APIRouter(prefix="/api", tags=[...])`, DI DuckDB)

- `api/routers/tickets.py` — `GET /api/tickets` → `list[Ticket]`.
- `api/routers/alerts.py` — `GET /api/alerts/{id}` → `DispatchAlert` (404 если нет).
- `api/routers/trips.py` — `GET /api/trips/{id}` → `TripDossier` (404 если нет).

## Edge cases / поведение

- Нет `output/actions.csv` (или пустой/только заголовок) → `list_tickets` возвращает `[]` (не ошибка).
- `Ticket.status` дефолт `"active"` (единый enum §3.1), **не** `"new"`; `is_overdue = deadline<now И status∉{closed}`; `deadline=null` → `is_overdue=false`; `status="closed"` → `is_overdue=false` даже при просроченном `deadline`.
- `DispatchAlert.video_window_sec` всегда `15` (фиксировано контрактом §7.5).
- `get_alert`/`get_trip` по неизвестному `id` → `None` (роутер → 404), не пустой объект.
- `TripDossier.timeline[*].has_video: bool` — `true` только если у алярма есть скачанный видеоканал; пустая поездка → `track=[]`/`timeline=[]` (валидный ответ, не 404, если ТС/поездка существует).

## Check

- `GET /api/tickets` без `output/actions.csv` возвращает `[]`; после записи действия (POST /api/actions) — строку с этим `incident_id`/`action`/`comment` и `status="active"`.
- Просроченная заявка (`deadline<now`, `status∉{closed}`) → `is_overdue=true`; та же заявка со `status="closed"` или `deadline=null` → `is_overdue=false`.
- `GET /api/alerts/{id}` для существующего инцидента возвращает `DispatchAlert` с `video_window_sec=15` и вложенным `IncidentDetail`.
- `GET /api/trips/{id}` возвращает `TripDossier`: `track` — массив `TelemetryPoint`, `timeline` — массив событий с `has_video` (bool).
- Неизвестный `id` в `/alerts`/`/trips` → 404 (сервис вернул `None`).
- `from api.services.tickets_service import list_tickets, get_alert, get_trip` импортируется.
