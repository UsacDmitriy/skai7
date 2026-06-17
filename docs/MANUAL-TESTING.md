# MANUAL-TESTING — чек-лист ручного прохода SKAI

QA-сценарий по запущенному приложению. Установка и запуск — в [`RUNBOOK.md`](RUNBOOK.md).
Этот документ: что кликать, на каких данных и какой результат ожидать.

## 0. Подготовка

```bash
make db          # data/skai.duckdb (идемпотентно)
make seed        # справочник водителей + датасет обучения
make api         # FastAPI → http://localhost:8000  (терминал 1)
make web         # Vite     → http://localhost:5173  (терминал 2)
```

Проверка живости одной командой:

```bash
curl -s http://localhost:8000/api/health        # {"status":"ok"}
curl -s http://localhost:8000/api/incidents | head -c 200
```

> Без `GROQ_API_KEY` копилот и голос работают на локальном regex-fallback — это норма.

## 1. Эталонные данные (из текущего датасета)

| Что | Значение |
|---|---|
| ТС из справочника (21 шт.) | `A079AM250`, `M477YM790`, `В224ВВ125` |
| Инцидент с видео (FCW) | `6f7ba1fa-dbe7-4096-bb1d-1b01bf7b5eb0` (`Т266АК977`) |
| Инцидент с видео (DMS, курение) | `e51a3984-2706-4972-b850-d424435dcd11` (`М083ОУ124`) |
| Всего инцидентов | 55 · зон 29 · заявок 8 · водителей 21 |

## 2. Поэкранный чек-лист (UI `:5173`)

| # | Экран / маршрут | Действие | Ожидаемо |
|---|---|---|---|
| 1 | Лента `/events` | открыть | список инцидентов, бейджи риска, фильтры работают |
| 2 | Монитор `/monitor` | открыть | живые алерты, реакция-кнопки |
| 3 | Карточка `/incidents/{id}` | открыть инцидент **с видео** (см. §1) | плеер тянет mp4 (Network: `206 Partial Content`), карта трека, телеметрия |
| 4 | — | блок «Водитель» на карточке | **регион/отдел/safety_score совпадают с отчётом водителя** (см. §3) |
| 5 | Отчёт `/report` | ввести ФИО или № ТС | KPI, нарушения, дисциплинарный флаг, блок позитивного вождения |
| 6 | Лидерборд `/leaderboard` | открыть | 21 строка, `unified_score` по убыванию, клик → отчёт водителя |
| 7 | Заявки `/tickets` | открыть | 8 заявок, смена статуса |
| 8 | Валидация `/validation` | открыть | 7 проверок консистентности, статусы ok/warn/fail, примеры |
| 9 | Рейс `/trip/{id}` | перейти из карточки/ленты | досье рейса, кросс-ссылки |
| 10 | РЭБ `/reb/{id}` | открыть | блок восстановления РЭБ |
| 11 | Здоровье парка `/fleet-health` | открыть | сводка; дрилл `→ fuel/{plate}`, `→ sensors/{plate}` |
| 12 | Навигация `/navigation` | открыть | проблемные участки GPS |
| 13 | Метрики `/metrics` | открыть | AI-метрики + data-quality |
| 14 | Копилот `/copilot` | спросить «сколько инцидентов?» | осмысленный ответ (regex-fallback без ключа) |

## 3. Ключевой сценарий консистентности (регресс-проверка)

Один водитель — одинаковые регион/отдел/safety_score **на всех экранах**.

1. Открой `/incidents/{id}` для ТС, например `A079AM250` → запомни «Регион», «safety_score».
2. Открой `/report`, найди того же водителя → значения **должны совпасть**.

Проверка по API:

```bash
P=A079AM250
# инцидент этого ТС:
IID=$(curl -s "http://localhost:8000/api/incidents" \
  | python3 -c "import sys,json;print(next(i['id'] for i in json.load(sys.stdin) if i['vehicle_plate']=='$P'))")
curl -s "http://localhost:8000/api/incidents/$IID" \
  | python3 -c "import sys,json;d=json.load(sys.stdin);print('incident safety_score:',d['driver_safety_score'],'| регион:',d['driver_region'])"
curl -s "http://localhost:8000/api/reports/driver/$P" \
  | python3 -c "import sys,json;d=json.load(sys.stdin);print('report   safety_score:',d['driver']['safety_score'])"
# safety_score инцидента и отчёта должны совпасть (оба из driver_reference §7.1) — рассинхрона быть не должно.
```

## 4. Граничные случаи (ожидаемые 4xx — это корректно)

| Запрос | Код | Смысл |
|---|---|---|
| `GET /api/incidents/НЕСУЩЕСТВУЕТ` | 404 | нет инцидента |
| `GET /api/incidents/{id}/video/9` | 404 | неверный канал |
| `GET /api/driver-score/XX000XX000` | 404 | ТС не в справочнике |
| `GET /api/positive-score/XX000XX000` | 404 | ТС не в справочнике |
| `POST /api/copilot/chat` без `text` | 422 | обязательное поле `text` |

> Списки `alerts`/`trips` доступны только по id (`/api/alerts/{id}`, `/api/trips/{id}`) —
> на них переходят из ленты/монитора, отдельного list-эндпоинта нет (by design).

## 5. Автоматические гейты перед релизом

```bash
make test            # pytest (639) + vitest (233) — оба зелёные
make typecheck       # tsc --noEmit
make openapi         # docs/openapi.json синхронен с живой схемой (git diff пуст)
```
