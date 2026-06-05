# Дефекты барьер-волны (smoke x3 / x4a)

> Журнал заводится smoke-прогонами (`x3-e2e-smoke.md`, `x4a-smoke-reports-voice.md`).
> Smoke ничего не чинит сам — только фиксирует дефект и адресует его соответствующему
> треку (B/F/T). Чинить — на ветке `integration`, после фикса перезапустить smoke.

---

## DEF-1 · `GET /incidents/{id}/video/{channel}` всегда 404 при наличии файла

- **Дата:** 2026-06-04 (smoke x3)
- **Трек:** B (backend) · `b6-routers` / `core/config.py`
- **Severity:** P0 — happy-path видеодоказательств сломан (видео не отдаётся никогда).
- **Статус:** ✅ RESOLVED (2026-06-04) — `_resolve_media_path()` в `api/routers/incidents.py`
  снимает избыточный префикс `datasets/media` перед склейкой с `media_dir`.
  Проверено: `GET …/video/5` → `200 video/mp4` (1.8 МБ). Покрыто `test_incidents_api.py`.

### Симптом
Для алярма с реально скачанным видео на диске эндпоинт отдаёт `404`:

```
ID=ea559499-85da-46f3-8990-f9bd43ee96ac   # Distraction, ch5 download_status=downloaded
GET /api/incidents/$ID/video/5  →  404  {"detail":"Видеофайл отсутствует на диске"}
```

Файл при этом существует:
`datasets/media/video_events/M083OU124__202605141918__Distraction__alarm_ea559499__ch5__d170eab3-...mp4`

### Корень
Двойной префикс `datasets/media`:

- `incidents_repo.video_path_for()` возвращает `media_relative_path` **относительно корня проекта** —
  значение уже содержит `datasets/media/video_events/...`.
- `api/core/config.py:27` → `media_dir = _PROJECT_ROOT / "datasets" / "media"`.
- `api/routers/incidents.py:81` → `file_path = settings.media_dir / rel_path`.

Итог склейки:
```
/…/skai_7/datasets/media/ datasets/media/ video_events/…mp4   ← такого пути нет → 404
```

Проверка:
```python
from api.core.config import settings
rel = "datasets/media/video_events/M083OU124__…__ch5__….mp4"
(settings.media_dir / rel).is_file()   # False  (двойной datasets/media)
__import__("os").path.isfile(rel)      # True   (путь корректен от корня проекта)
```

### Варианты фикса (решение за треком B)
1. `media_dir = _PROJECT_ROOT` в `core/config.py` (т.к. `media_relative_path` уже включает `datasets/media/`), **или**
2. хранить/возвращать в `video_path_for()` путь относительно `datasets/media` (без префикса), **или**
3. в роутере: `file_path = settings.project_root / rel_path` для media_relative_path.

### Покрытие тестами (трек T)
`api/tests/test_b5_schemas_services.py` проверяет `repo.video_path_for()` (строку), но **не** полный
эндпоинт с `FileResponse` и склейкой `media_dir / rel_path` — поэтому дефект не пойман.
Добавить в `test_incidents_api.py` (T) кейс: алярм с `download_status='downloaded'` → `200`, `content-type: video/mp4`.

---

## DEF-2 · Отсутствует `api/tests/test_incidents_api.py` (трек T)

- **Дата:** 2026-06-04 (smoke x3)
- **Трек:** T (tests) · `t2`
- **Severity:** P2 — smoke-шаг pytest по incidents API не покрыт авторскими тестами.
- **Статус:** ✅ RESOLVED (2026-06-04) — добавлен `api/tests/test_incidents_api.py`
  (`TestClient`: список+обогащение / деталь / 404 / invalid-channel 404 / missing-incident 404 /
  **200 video happy-path** / 501 на fuel·sensors·navigation). Полный набор: 108 passed.

`x3` ожидал `test_incidents_api.py` (`TestClient`: список / деталь / 404 на несуществующий id /
501 на fuel / **200 video happy-path** — см. DEF-1). Ранее были только `test_enrichment.py`
и `test_b5_schemas_services.py` (эндпоинт-уровень incidents не покрывался — поэтому DEF-1 не ловился).

---

## DEF-3 · Фронт биндит сырой `cam_*_url` вместо `videoUrl()` — видео не грузится в браузере

- **Дата:** 2026-06-04 (обнаружено при фиксе DEF-1)
- **Трек:** F (frontend) · `IncidentCard` / `Report`
- **Severity:** P1 — даже с рабочим эндпоинтом (DEF-1) плееры не получают видео.
- **Статус:** ✅ RESOLVED (2026-06-05) — `IncidentCard.tsx` и `Report.tsx` теперь строят
  `src` через `client.videoUrl(inc.id, channel)` (ADAS→1, DMS→5, `cam_extra`→`cam.channel`),
  сохраняя «нет видео → пустое состояние». Проверено в браузере: `GET …/video/1` и `…/video/5`
  → `206 Partial Content` (плеер тянет mp4). `npm run typecheck` зелёный.

### Симптом
`IncidentCard.tsx:346/355` и `Report.tsx:309/310` передают в `<VideoPlayer src>` напрямую
`inc.cam_front_url` / `inc.cam_dms_url` — а это сырые пути из БД (`datasets/media/video_events/…mp4`).
Как относительный URL на странице `/incidents/{id}` он резолвится в
`http://localhost:5173/incidents/datasets/media/…` → 404 (Vite такое не отдаёт).

### Корень
В `web/src/api/client.ts:107` уже есть хелпер `videoUrl(id, channel)` →
`${BASE}/incidents/{id}/video/{channel}` (рабочий эндпоинт), но `IncidentCard`/`Report`
его не используют — биндят строковое поле напрямую.

### Фикс (трек F)
- ADAS/фронт → `videoUrl(inc.id, 1)`, DMS/салон → `videoUrl(inc.id, 5)`;
  сохранить «нет видео → пустое состояние»: `src = inc.cam_front_url ? videoUrl(inc.id, 1) : undefined`.
- То же для `cam_extra[]` (каналы 2/3) и для `Report.tsx`.

---

## DEF-4 · `api/routers/reports.py` не перевязан на сервис b9/b10 — vehicle/transcribe/query(text) недоступны

- **Дата:** 2026-06-05 (smoke x4a · Барьер 2.1)
- **Трек:** B (backend) · `d5` (reports/voice wiring) · `api/routers/reports.py`
- **Severity:** P0 — killer-feature «голос→NLU→отчёт» (идея #4) и разрез В-2/ТС (идея #2)
  end-to-end сломаны: фронт `f7` готов и тайпчек зелёный, но 3 из 5 эндпоинтов среза не отвечают.
- **Статус:** ✅ RESOLVED (2026-06-05) — роутер перевязан на сервис: добавлены
  `GET /vehicle/{plate}` → `vehicle_report` (`cameras` len=3), `POST /query` принимает
  `{text, period_days?}` → `reports_service.query` (`{query, report}`), `POST /transcribe`
  (multipart `file`+`lang`) → `stt_service`. В `requirements.txt` добавлен **`python-multipart`**
  (обяз. для multipart; раньше отсутствовал — transcribe падал бы на старте) + `faster-whisper`/`groq`.
  Срез закоммичен в `feat/backend`/`feat/web` и слит в `integration` (был uncommitted — мерж был no-op).
  Повторный smoke на `integration` зелёный: все 5 эндпоинтов 200 (`query.kind` driver+fleet через
  regex-fallback без `GROQ_API_KEY`; `transcribe`→`{text,lang,confidence}`); `pytest` 157 passed;
  `npm run typecheck` зелёный. **К Волне 2.2 можно переходить.**

### Симптом

Сервис- и data-слой Волны 2.1 готовы (`make db` зелёный: `driver_reference`=21, `driver_trips`=33,
view `v_driver_report`/`v_fleet`/`v_vehicle` существуют), но **роутер остался версии b5** — экспонирует
только `driver/fleet/query(ReportQuery)`. Прогон против живого API (`uvicorn :8011`):

```text
GET  /api/reports/driver/{plate}        -> 200  ✅ kpi, disciplinary_warning=true, violations[].is_gross=true (§7.5 OK)
GET  /api/reports/fleet?view=drivers    -> 200  ✅ by_drivers=21, by_vehicles=21 (оба разреза)
GET  /api/reports/fleet?view=vehicles   -> 200  ✅
GET  /api/reports/vehicle/{plate}       -> 404  ❌ эндпоинт не зарегистрирован
POST /api/reports/query  {text:"…"}     -> 422  ❌ {detail: body.kind Field required} — роутер ждёт ReportQuery, не {text}
POST /api/reports/transcribe (wav)      -> 404  ❌ эндпоинт не зарегистрирован
```

`GET /openapi.json` → под `/reports` зарегистрированы только `driver/{plate}`, `fleet`, `query`.

### Корень

`api/routers/reports.py` (комментарий в шапке всё ещё «реальный NLU-парс ... придёт в b9») вызывает
`reports_service.report_for_query(ReportQuery)` напрямую и не подключён к уже готовым функциям сервиса:

- `reports_service.vehicle_report(db, plate, period_days)` — есть (строка ~252), **эндпоинта нет**;
- `reports_service.query(db, text, period_days)` → возвращает `{"query": ReportQuery, "report": …}`
  через `nlu_service.parse(text)` — есть (~355), **роутер его не зовёт** (берёт уже разобранный `ReportQuery`);
- `stt_service` (faster-whisper, `transcribe`) — есть, **эндпоинта `POST /transcribe` нет**.

Фронт `f7` уже бьёт в `client.ts` → `/reports/transcribe` и `/reports/query` (text) — оба контракта
со стороны фронта правильные; рассинхрон только в роутере бэка.

### Фикс (за треком B — barrier ничего не переписывает)

В `api/routers/reports.py` добавить/перевязать (response-model из `api/domain/reports.py`, всё уже есть):

1. `GET /vehicle/{plate}` → `reports_service.vehicle_report(db, plate, period_days)` (`VehicleReport`, `cameras` длины 3).
2. `POST /query` → принимать `{text: str, period_days?: int}` и звать `reports_service.query(db, text, period_days)`;
   вернуть `{query, report}` (`query.kind="driver"|"fleet"`). Без `GROQ_API_KEY` — fallback regex в `nlu_service`.
3. `POST /transcribe` → `UploadFile` (wav multipart) → `stt_service` → `{text, lang, confidence}`.

После фикса: перезапустить `x2-wiring` (авто-обход роутеров) и `x4a`-smoke; ожидаемый зелёный —
все 5 эндпоинтов + e2e `f7`.

### Процессная заметка (assembly)

Работа Волны 2.1 на момент барьера **не закоммичена**: `feat/backend`/`feat/web` стоят на коммите
`integration` (`cd0c113`), изменения висят в worktree как uncommitted/untracked. Поэтому
`git merge feat/backend feat/web` из шага «склейка» — no-op и **не переносит срез на `integration`**.
Smoke выполнен по коду в worktree (`.worktrees/backend`, `.worktrees/web`). Перед фиксом DEF-4 треки
должны закоммитить срез 2.1 в свои ветки, иначе мерж в `integration` ничего не подтянет. `main` не тронут.
