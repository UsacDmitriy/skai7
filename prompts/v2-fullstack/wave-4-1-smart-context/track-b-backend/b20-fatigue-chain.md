# b20 · Fatigue chain — цепочки усталости (идея #15)

> Трек **Backend/Data**. Против `00-CONTRACT.md` §8.3/§8.4. **Владеет:** `api/services/fatigue_service.py`,
> роутер `api/routers/fatigue.py` (автодискавери `api/main.py:_discover_routers` — объяви `router = APIRouter(...)`
> в своём файле; **НЕ** редактируй общий `api/routers/__init__.py`, иначе гонка с b18/b19).
> **Модель:** 🔵 Sonnet — детерминированная темпоральная корреляция; гейт = тесты.
> **Волна 4.1**, окно 1 (backend). Зависит от: каталог алярмов (`DMS_YAWNING`/`DMS_DROWSY`/harsh-коды), `ts`/plate.

## Цель

Раннее предупреждение усталости: найти **цепочки** событий по водителю/рейсу в скользящем окне
(`YAWNING → DROWSY → harsh-событие`), которые по отдельности слабее, но вместе сигналят о деградации.
`GET /api/fatigue?plate=` → `FatigueChain[]` (§8.4).

## Состав

- `fatigue_service.chains(plate=None) -> list[FatigueChain]`:
  - Сортировка алярмов водителя по `ts`; скользящее окно `window_min` (дефолт 90).
  - Цепочка = ≥2 связанных события усталости/риска в окне (`DMS_YAWNING`, `DMS_DROWSY`,
    `HARSH_BRAKING`, `HARSH_ACCEL`, `HARSH_CORNERING`); `severity` растёт с длиной цепочки и наличием `DMS_DROWSY`.
  - `events: {code, ts}[]`, `trip_id?` (если события одного рейса), `window_min`.
- Роутер `GET /api/fatigue` (опц. `?plate=`); нет цепочек → `[]`.

## Зависимости

Без сети/ML — чистая логика по времени. Детерминизм: без `datetime.now()`, окна от `ts` событий.

## Check

- `GET /api/fatigue` → 200 `FatigueChain[]`; цепочка `yawning→drowsy→harsh` в окне найдена.
- Одиночное событие или события вне окна → НЕ цепочка.
- `?plate=` фильтрует по водителю; нет цепочек → `[]`.
- `severity` монотонно растёт с длиной/тяжестью; детерминированно между прогонами.

## Коммит (обязательно)

Заверши промпт коммитом в свою ветку — **merge на барьере берёт только коммиты**.
⚠️ **Параллельно с b18/b19 в одном worktree — НЕ `git add -A`**: стейджи только свои файлы
(иначе коммит подхватит недописанные файлы соседей, как в w3-17/w3-18). Доп. свои файлы — добавь явно.

```bash
git add api/services/fatigue_service.py api/routers/fatigue.py
git commit -m "b20: <что сделано>"
```
