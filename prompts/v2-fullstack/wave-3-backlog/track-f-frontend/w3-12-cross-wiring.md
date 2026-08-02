# W3-12 · Кросс-врезки экранов (целостность навигации между экранами)

> Волна 3 · бэклог. Трек **Frontend**. Против `00-CONTRACT.md` **§9.4** (кросс-врезки) + §7.4/§7.5.
> **Исполнение:** bounded ClinePass package; role `worker`; route category `code`; exact route/model only from `tools/clinepass-mcp/models.env` — аддитивная вёрстка/навигация против контракта; гейт = секция Check.
> **Владеет (правки строго аддитивные, killer-features не ломать):** `web/src/pages/IncidentCard.tsx`,
> `TripDossier.tsx`, `Report.tsx`, `EventsFeed.tsx`. Использует клиент w3-10 (`getTickets` уже есть). **Не блокирует** P0/P1/P2.

## Контекст (экраны-сироты + незамкнутые петли)

Аудит выявил: `/trip/:id` и `/reb/:id` достижимы только по URL; карточка инцидента создаёт заявки, но не
показывает их и не ведёт в `/tickets`; нарушения/парк в отчётах не доводят до карточки инцидента.
Ключевой факт: **`trip_id == incident_id`** (`api/routers/trips.py` → `tickets_service.get_trip` →
`repo.get_incident(db, trip_id)`) — связать инцидент↔маршрут тривиально.

## Что сделать (точки врезки подтверждены по исходникам)

1. **`IncidentCard.tsx`**:
   - Кнопка **«Показать маршрут поездки»** → `navigate('/trip/' + inc.id)` (топбар-`Card`, ~стр.351–393; иконка `Route`).
   - Блок **«Связанные заявки»** (новый `Card` в правой колонке, после блока «Действия», ~после стр.622):
     на маунте `client.getTickets()` → `filter(t => t.incident_id === inc.id)`; каждая строка — `Link`
     в `/tickets`; пусто → «Заявок по инциденту нет».
   - В `runAction` (~стр.234–256) при `action === 'create_task'` — в `actionFeedback` добавить ссылку
     **«Открыть в Заявках»** → `/tickets` (блок фидбэка ~стр.608–621).
2. **`TripDossier.tsx`**: бэк-ссылка **«К карточке инцидента»** → `navigate('/incidents/' + id)` (`id` — параметр
   маршрута = incident_id; в шапке-`Card`, иконка `ArrowLeft`). Закрывает петлю IncidentCard↔TripDossier.
3. **`Report.tsx`**:
   - Строка нарушения — **доп. ссылка** → `/incidents/${r.id}` (колонка-иконка `ExternalLink` в
     `VIOLATION_COLUMNS`, ~стр.185–191). **Инлайн-видео по клику строки сохранить** (killer-feature) —
     ссылка аддитивна.
   - Строки fleet-отчёта (`FLEET_DRIVER_COLUMNS`/`FLEET_VEHICLE_COLUMNS`, ~стр.193–208) — drill:
     водитель → re-query как `DriverReport` (через существующий `runQuery` с `driver_name`); ТС → перейти
     в фильтрованную ленту (`/?plate=...`) **или** `DriverReport` (выбрать один путь, без новой страницы).
4. **`EventsFeed.tsx`**: в строке (`EventRow`, ~стр.383–389) — иконка-экшен **«Маршрут»** → `/trip/${row.id}`
   с `e.stopPropagation()` (чтобы не сработала навигация строки в инцидент).

## Check

- В `/incidents/:id`: есть кнопка «Показать маршрут поездки» → открывает `/trip/<тот же id>`; блок «Связанные
  заявки» фильтрует по `incident_id`; после «Создать заявку» в фидбэке есть ссылка «Открыть в Заявках».
- В `/trip/:id`: есть «К карточке инцидента» → `/incidents/<id>` (петля замкнута).
- В `/report`: строка нарушения имеет ссылку в `/incidents/:id` **и** по-прежнему открывает инлайн-видео;
  строки парка кликабельны (drill работает).
- В `/` (лента): иконка «Маршрут» в строке открывает `/trip/:id`, не открывая попутно карточку инцидента.
- На живом API и фикстурах (`VITE_USE_FIXTURES=true`); `npm run typecheck` зелёный; a11y ссылок/кнопок (focus, aria-label).

## Коммит (обязательно)

```bash
git add -A && git commit -m "w3-12: кросс-врезки (incident↔trip↔tickets, report→incident, feed→trip)"
```
