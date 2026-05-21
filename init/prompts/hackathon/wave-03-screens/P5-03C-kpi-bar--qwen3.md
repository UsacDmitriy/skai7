# 03C · KPIBar.tsx
> 🤖 **Модель: `qwen/qwen3-coder:free`** | кодинг
> 💰 **Бюджет:** читать max 1–3 файла · не читать `./data`, `.venv`, `node_modules` · логи: 20–50 строк
> ⚠️ **Один промпт = одна сессия Cherry Studio.** Не запускать параллельно.

> Волна 3

**Файл:** `code/frontend/src/components/KPIBar.tsx`

Передать: `code/frontend/src/types.ts` + `code/frontend/src/constants.ts`., `types.ts`.

Props: `incidents: Incident[]`

**5 карточек** в ряд (`flex gap-0 bg-white border-b border-skai-border`).  
Каждая карточка: `px-6 py-4 border-r border-skai-border`.

| Лейбл | Формула |
|-------|---------|
| ТС В ЗОНЕ РИСКА | `filter(riskLevel critical или high).length` |
| КРИТИЧНЫХ | `filter(riskLevel critical).length` |
| ВСЕГО ЗАЯВОК | `incidents.length` |
| ПРОСРОЧЕНО | `filter(dueDateStr && overdue).length` |
| УСТРАНЕНО | `filter(status closed).length` |

Цифра: 28px bold `skai-primary`.  
Лейбл: 11px uppercase `skai-muted`.

Экспорт: `export default KPIBar`
