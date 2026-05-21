# 02C · TelemetryChart.tsx
> 🤖 **Модель: `qwen/qwen3-coder:free`** | кодинг
> 💰 **Бюджет:** читать max 1–3 файла · не читать `./data`, `.venv`, `node_modules` · логи: 20–50 строк
> ⚠️ **Один промпт = одна сессия Cherry Studio.** Не запускать параллельно.

> Волна 2

**Файл:** `code/frontend/src/components/TelemetryChart.tsx`

Передать: `code/frontend/src/types.ts` + `code/frontend/src/constants.ts`., `code/frontend/src/types.ts` (тип `TelemetryPoint`), `code/frontend/src/constants.ts`.

```ts
import { ComposedChart, Line, XAxis, YAxis, CartesianGrid,
         Tooltip, ReferenceLine, ResponsiveContainer } from 'recharts';
```

**Props:**
```ts
incident: Incident          // incident.telemetry: TelemetryPoint[] — tsOffset, speedKmh, accelX
currentOffsetSec: number | null   // от VideoEvidencePanel.onTimeUpdate
```

**Данные:**
```ts
const data = incident.telemetry.map((p: TelemetryPoint) => ({
  offset: p.tsOffset, speed: p.speedKmh, accel: p.accelX
}));
```

**Chart (height 200px):** `ResponsiveContainer width="100%"`
- `XAxis` dataKey="offset" domain={[-60,30]} tickFormatter={v=>`${v}с`}
- `YAxis` left: скорость 0–140 км/ч, right: акселерометр −6–6 м/с²
- `CartesianGrid` strokeDasharray="3 3" stroke="#E2E8F0"
- `Tooltip` с русскими лейблами: "Скорость" / "Акселерометр"
- `ReferenceLine x={0}` — красная вертикаль "Событие"
- `ReferenceLine y={incident.speed_limit_kmh}` — оранжевый пунктир "Лимит"
- `ReferenceLine x={currentOffsetSec}` — синяя вертикаль (видео-маркер, только если не null)
- `Line` скорость: stroke="#1E3A8A" strokeWidth=2 dot=false
- `Line` акселерометр: stroke="#EA580C" strokeWidth=1.5 dot=false

**Легенда** под графиком (flex gap-4 text-xs text-skai-muted):
`━ Скорость CAN` | `━ Акселерометр` | `╌ Событие t=0`

**Check:** Рендерится без ошибок для всех 8 кейсов включая inc-006 (пустая телеметрия → пустой граф, не краш).
