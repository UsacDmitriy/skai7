# 01B · constants.ts
> 🤖 **Модель: `qwen/qwen3-coder:free`** | кодинг
> 💰 **Бюджет:** читать max 1–3 файла · не читать `./data`, `.venv`, `node_modules` · логи: 20–50 строк
> ⚠️ **Один промпт = одна сессия Cherry Studio.** Не запускать параллельно.

> Волна 1

**Файл:** `code/frontend/src/constants.ts`  
**Только этот файл.**

Передать: `code/frontend/src/types.ts` + `code/frontend/src/constants.ts`.`hackathon/context/DESIGN.md`.  
Экспортируй константы:

```ts
COLORS        // primary #1E3A8A, bg #F8FAFC, text #0F172A, muted #64748B,
              // border #E2E8F0, critical #DC2626, warning #EA580C, ok #16A34A

RISK_BADGE    // Record<RiskLevel, {bg, text, dot}> — цвета бейджей
STATUS_BADGE  // Record<Incident['status'], {bg, text, label}>
EVENT_LABELS  // Record<EventType, string> — все 13 типов на русском
SOURCE_STATUS_LABEL // Record<SourceStatus, string>
```

Используй `as const`. Импортируй `RiskLevel`, `EventType` и др. из `./types`.  
**Check:** `tsc --noEmit` без ошибок.
