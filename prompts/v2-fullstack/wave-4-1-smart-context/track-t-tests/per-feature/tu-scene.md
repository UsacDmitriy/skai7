# tu-scene · Unit-тесты scene-context (идея #11, модуль b16)

> Трек **Tests** (`feat/tests`, окно 3). Против `00-CONTRACT.md` §8.1.
> **Исполнение:** bounded ClinePass package; role `worker`; route category `code`; exact route/model only from `tools/clinepass-mcp/models.env` — детерминированная логика против контракта; гейт = pytest.
> **Владеет:** `api/tests/unit/test_scene_context.py`. Инфра — из `t1`. Гонится после `b16`.

## Цель

Покрыть детерминизм и форму кэша сцены без VLM и без сети (на готовом `data/ai/scene_labels.json`).

## Состав — `api/tests/unit/test_scene_context.py`

- `incident_scene` имеет ровно 54 строки (1 на алярм), значения полей — из enum §8.1, без NULL.
- Кэш детерминирован: повторная сборка из того же JSON даёт идентичную таблицу.
- Кадр отсутствует → строка `scene_confidence=0`, поля `unknown`, не падает.
- Рантайм-чтение `incident_scene` не требует VLM-зависимости (импорт сервиса без неё).

## Check

- `pytest api/tests/unit/test_scene_context.py -q` зелёный без сети и без VLM.
- Enum-валидация полей; 54 строки; кейс «нет кадра» обработан.

## Коммит (обязательно)

Заверши промпт коммитом в свою ветку — **merge на барьере берёт только коммиты**.
⚠️ **5× tu-* идут параллельно в одном tests-worktree — НЕ `git add -A`**: стейджи только свой тест-файл
(иначе коммит подхватит недописанные тесты соседей).

```bash
git add api/tests/unit/test_scene_context.py
git commit -m "tu-scene: <что сделано>"
```
