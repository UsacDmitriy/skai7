# 02F · IncidentTopBar.tsx
> 🤖 **Модель: `qwen/qwen3-coder:free`** | кодинг
> 💰 **Бюджет:** читать max 1–3 файла · не читать `./data`, `.venv`, `node_modules` · логи: 20–50 строк
> ⚠️ **Один промпт = одна сессия Cherry Studio.** Не запускать параллельно.

> Волна 2

**Файл:** `code/frontend/src/components/IncidentTopBar.tsx`

Передать: `code/frontend/src/types.ts` + `code/frontend/src/constants.ts`.

Props: `incident: Incident`, `onBack: () => void`

**Высота 56px**, `bg-white border-b border-skai-border`, flex items-center px-6 gap-4.

Три зоны:
```
LEFT:   <button onClick={onBack}>← Назад</button>
        "|" (muted)
        "{plate} — {driverName}" (text-sm muted)

CENTER: EVENT_LABELS[eventType] (font-semibold text-sm)
        время события (toLocaleString ru-RU)

RIGHT:  Risk badge — цвет из RISK_BADGE[riskLevel]
        "Score {score}" — bold, цвет по riskLevel
```

Risk badge: `text-xs px-2 py-1 rounded-full font-medium`.  
Score цвет: ≥80 → critical, 50–79 → warning, <50 → ok.

Экспорт: `export default IncidentTopBar`
