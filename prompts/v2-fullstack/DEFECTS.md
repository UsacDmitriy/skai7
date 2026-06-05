# Дефекты барьер-волны (smoke x3)

> Журнал заводится smoke-прогоном `x3-e2e-smoke.md`. Smoke ничего не чинит сам —
> только фиксирует дефект и адресует его соответствующему треку (B/F/T).
> Чинить — на ветке `integration`, после фикса перезапустить smoke.

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
