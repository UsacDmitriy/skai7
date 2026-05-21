# 02E · SourceStatusGrid.tsx
> 🤖 **Модель: `qwen/qwen3-coder:free`** | кодинг
> 💰 **Бюджет:** читать max 1–3 файла · не читать `./data`, `.venv`, `node_modules` · логи: 20–50 строк
> ⚠️ **Один промпт = одна сессия Cherry Studio.** Не запускать параллельно.

> Волна 2

**Файл:** `code/frontend/src/components/SourceStatusGrid.tsx`

Передать: `code/frontend/src/types.ts` + `code/frontend/src/constants.ts`., `code/frontend/src/types.ts` (типы `Vehicle`, `SourceStatus`), `code/frontend/src/constants.ts`.

**Props:** `incident: Incident`

```ts
import vehiclesData from '../../data/mock/vehicles.json';
const vehicle = (vehiclesData as Vehicle[]).find(v => v.plate === incident.vehicle_plate); // vehicles.json: V-001..V-006; связь через vehicle_plate
```

**Заголовок секции:** `СОСТОЯНИЕ КОМПЛЕКСА` (text-xs uppercase text-skai-muted mb-2)

**4 системных строки** (flex items-center gap-2 py-1.5 text-sm):
```
📡 Связь       vehicle.connectionStatus
🔋 Питание     vehicle.powerStatus  (fallback: 'online')
💾 Архив       vehicle.archiveStatus
🔧 Калибровка  vehicle.calibrationRequired ? 'warning' : 'online'
```

**Строки камер** из `vehicle.cameras`:
```
📷 {camera.label}   camera.status
```

**Бейдж статуса** (text-xs px-2 py-0.5 rounded-full font-medium):
```ts
const badge: Record<SourceStatus, {bg: string; text: string; label: string}> = {
  online:  { bg: 'bg-green-100', text: 'text-green-800', label: 'Онлайн'         },
  offline: { bg: 'bg-red-100',   text: 'text-red-800',   label: 'Нет сигнала'    },
  warning: { bg: 'bg-amber-100', text: 'text-amber-800', label: 'Требуется'      },
  unknown: { bg: 'bg-slate-100', text: 'text-slate-600', label: 'Нет данных'     },
};
```

Если `vehicle` не найден — показать `<div className="text-xs text-skai-muted">Данные ТС недоступны</div>`, не крашиться.

**Check:**
- inc-001 → все бейджи green "Онлайн"
- inc-003 → CAM-03 badge red "Нет сигнала", badge "Требуется" у калибровки
