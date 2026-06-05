# W3-1 · Синхронизация промпта b13 с contract-change #1 (Ticket)

> Волна 3 · бэклог. Трек **Backend/Data** (владелец `b13`). Против `00-CONTRACT.md`
> **Модель:** 🔵 Sonnet — детерминированная логика/вёрстка против контракта; гейт = секция Check.
> changelog #1 (b) и §7.5. **Владеет:** правкой текста `prompts/v2-fullstack/wave-2-2-applied/track-b-backend/b13-tickets-alerts-trips.md`
> (и, если `tickets_service.py` уже реализован, — приведением его к новому enum).
> **Не блокирует** P0/P1/P2. Берётся, как только трек backend свободен; **до** реализации `tickets_service`.

## Контекст

Контракт §7.5 и changelog #1 (b) перевели `Ticket.status` на единый enum
`Status = active | in_progress | validated | closed` (значение `new` удалено), а «Просрочена»
сделали **производным оверлеем**, добавив поля:

```
Ticket { id, created_at, incident_id, action, comment, status: Status,
         deadline: str|null, is_overdue: bool }
# is_overdue = deadline < now И status ∉ {closed}; «Просрочена» — не статус, а оверлей по is_overdue
```

Эталон уже на новом enum: `IncidentDetail.status` дефолтит `"active"` (§7.5, строка 111),
`actions_service` пишет действия в новый enum. Промпт `b13` отстал: он всё ещё описывает дефолт
`status = "new"` и схему `Ticket{...,status}` без `deadline`/`is_overdue`.

## Что сделать

В `prompts/v2-fullstack/wave-2-2-applied/track-b-backend/b13-tickets-alerts-trips.md`:

1. В описании `list_tickets` (сейчас строки ~15–17): дефолт `status` — **`"active"`**, не `"new"`
   (значения `new` в enum `Status` больше нет).
2. В описании схемы `Ticket` добавить производные поля:
   - `deadline: str|null` — срок (ISO-8601 UTC) либо `null`, если не задан;
   - `is_overdue: bool` — вычисляется как `deadline < now() И status ∉ {closed}`; в UI это
     оверлей «⏱ Просрочено», **а не значение статуса**.
3. Если из CSV срок не известен — `deadline=null`, `is_overdue=false` (детерминированно, без обращения ко времени там, где срока нет).
4. В блоке **Check** добавить пункт: для тикета с `deadline` в прошлом и `status != "closed"`
   возвращается `is_overdue=true`; для `status="closed"` или `deadline=null` — `is_overdue=false`.

Если `api/services/tickets_service.py` к этому моменту **уже реализован** — синхронно привести его
к новому enum/полям (дефолт `"active"`, поля `deadline`/`is_overdue`) и обновить unit-тест.

## Check

- В `b13-tickets-alerts-trips.md` нет упоминаний значения `"new"`; дефолт статуса — `"active"`.
- Схема `Ticket` в промпте содержит `deadline` и `is_overdue` с формулой оверлея.
- Если сервис реализован: `list_tickets` возвращает `Ticket.status="active"` по умолчанию и корректный `is_overdue`.
- `grep -n '"new"' prompts/v2-fullstack/wave-2-2-applied/track-b-backend/b13-tickets-alerts-trips.md` — пусто.
