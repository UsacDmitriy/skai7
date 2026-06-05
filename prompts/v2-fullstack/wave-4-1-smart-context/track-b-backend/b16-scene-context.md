# b16 · Scene context — VLM по кадру (идея #11, предрасчёт)

> Трек **Backend/Data**. Против `00-CONTRACT.md` §8.1/§8.4. **Владеет:** `api/etl/scene_precompute.py`,
> `api/sql/30_incident_scene.sql`, `data/ai/scene_labels.json`.
> **Модель:** 🔴 Opus — VLM-пайплайн / новый домен / детерминизм оффлайн-предрасчёта.
> **Волна 4.1**, окно 1 (backend). Зависит от: b1 (ETL), b3 (`v_incidents`), видео ch1/ch5.

## Цель

Один раз **оффлайн** определить по кадру события (ADAS ch1 / DMS ch5) контекст сцены и закэшировать его,
чтобы рантайм демо читал готовую таблицу `incident_scene` без VLM и без сети.

## Состав

1. `api/etl/scene_precompute.py` — батч по 54 алярмам: берёт репрезентативный кадр (первый доступный
   `media_relative_path` ch1, иначе ch5), прогоняет через VLM (по умолчанию **локальный** Florence-2/Moondream
   ИЛИ Groq/Claude vision — выбор в конфиге), извлекает поля §8.1: `weather/day_night/road_surface/area/
   visibility/scene_confidence`. Результат пишет в `data/ai/scene_labels.json` (детерминированный кэш,
   сорт по `id`). Идемпотентно: повторный прогон при наличии кэша — no-op (флаг `--force` перезапускает).
2. `api/sql/30_incident_scene.sql` — `CREATE OR REPLACE TABLE "incident_scene"` из `read_json_auto('data/ai/scene_labels.json')`;
   ровно 1 строка на `id` из `v_incidents`; `source='cache'`. Префикс `30_` — порядок после view.
3. Если кадра/файла нет → строка с `source='cache'`, `scene_confidence=0`, поля `unknown` (не падать).

## Зависимости

VLM-зависимость — **только в `scene_precompute.py`** (ленивый импорт), в рантайме API не нужна.
Не читать видео целиком в Python без необходимости — брать один кадр (ffmpeg/opencv по таймстемпу).

## Check

- `python -m api.etl.scene_precompute` создаёт `data/ai/scene_labels.json` (54 записи) детерминированно.
- `make db` → `SELECT count(*) FROM "incident_scene"` = 54; поля из enum §8.1, без NULL.
- Повторный прогон без `--force` — no-op; с `--force` даёт идентичный JSON (детерминизм).
- Рантайм API/`make db` не требует VLM и сети.

## Коммит (обязательно)

Заверши промпт коммитом в свою ветку — **merge на барьере берёт только коммиты**; незакоммиченная
работа в worktree на барьер не попадёт:

```bash
git add -A && git commit -m "b16: <что сделано>"
```
