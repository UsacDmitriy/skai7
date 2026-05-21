# 05B · TicketsScreen.tsx
> 🤖 **Модель: `qwen/qwen3-coder:free`** | кодинг
> 💰 **Бюджет:** читать max 1–3 файла · не читать `./data`, `.venv`, `node_modules` · логи: 20–50 строк
> ⚠️ **Один промпт = одна сессия Cherry Studio.** Не запускать параллельно.

> Волна 5

**Файл:** `code/frontend/src/screens/TicketsScreen.tsx`  
**Только сборка KPIBar + фильтры + TicketsTable.**

Передать: `code/frontend/src/types.ts` + `code/frontend/src/constants.ts`. Убедись что `KPIBar` и `TicketsTable` существуют.

```ts
const [search, setSearch] = useState('');
const [statusFilter, setStatusFilter] = useState<'all'|Incident['status']>('all');

const rows = incidents
  .filter(i => statusFilter === 'all' || i.status === statusFilter)
  .filter(i => !search || i.plate.includes(search) || i.driverName.includes(search));
```

**Layout** (flex flex-col h-full):
```
<KPIBar incidents={incidents} />

{/* Filter bar */}
<div flex justify-between px-6 py-3 bg-white border-b>
  <input placeholder="Поиск по ТС или водителю..." />
  <select> Все / Новые / В работе / Закрытые </select>
</div>

<div flex-1 overflow-auto>
  <TicketsTable incidents={rows} onOpen={(id) => navigate(`/incident/${id}`)} />
</div>
```

**Check:** поиск "А777" → 1 строка. Клик "Открыть →" → /incident/inc-001.
