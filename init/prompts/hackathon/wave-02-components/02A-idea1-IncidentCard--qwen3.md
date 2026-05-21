# 02A · IncidentCard.tsx
> 🤖 **Модель: `qwen/qwen3-coder:free`** | кодинг
> 💰 **Бюджет:** читать max 1–3 файла · не читать `./data`, `.venv`, `node_modules` · логи: 20–50 строк
> ⚠️ **Один промпт = одна сессия Cherry Studio.** Не запускать параллельно.

> Волна 2

**Файл:** `code/frontend/src/components/IncidentCard.tsx`

Передавать контекст: `code/frontend/src/types.ts` + `code/frontend/src/constants.ts`.

**Props:**
```ts
incident:   Incident
isSelected: boolean
onClick:    () => void
```

**Layout** (карточка 100% ширина, white bg, padding 12px 14px,
border-left 4px solid по `risk_level`, border-bottom 1px #E2E8F0):

ROW 1 — flex justify-between:
  Left:  `{incident.vehicle_plate}` bold 14px + " — " + `{incident.driver}` 13px muted
  Right: time-ago из `incident.ts` (11px muted)

ROW 2 — mt-1:
  Dot ● цвет по `risk_level` + `incident.alarm_type_label` 13px bold

ROW 3 — chips mt-2 gap-2 text-xs (показывать только при условии):
  `incident.speed_kmh > 0`              → ⚡ {speed_kmh} км/ч
  `incident.is_night`                   → 🌙 Ночь
  `incident.continuous_driving_min > 120` → 🕐 {h}ч {m}мин
  `!incident.video_available`           → 📷 Нет видео (bg-red-50 text-red-600)

ROW 4 — Score bar mt-2:
  "Score" 11px muted + число bold (≥80 red, 50–79 orange, <50 green)
  div h=3px bg=#E2E8F0 → fill width={score}% цвет аналогично

Selected: bg-blue-50 + outline 1px #1E3A8A
Hover: bg-slate-50

```ts
// time-ago helper
const diff = (Date.now() - new Date(incident.ts).getTime()) / 1000;
if (diff < 3600) return `${Math.floor(diff/60)} мин назад`;
if (diff < 86400) return `${Math.floor(diff/3600)}ч назад`;
return new Date(incident.ts).toLocaleString('ru-RU', {day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'});
```

**Check:** рендерится без ошибок для inc-001..005. inc-003 показывает чип "📷 Нет видео".
