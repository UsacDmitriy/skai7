# 02G · ContextChips.tsx
> 🤖 **Модель: `qwen/qwen3-coder:free`** | кодинг
> 💰 **Бюджет:** читать max 1–3 файла · не читать `./data`, `.venv`, `node_modules` · логи: 20–50 строк
> ⚠️ **Один промпт = одна сессия Cherry Studio.** Не запускать параллельно.

> Волна 2

**Файл:** `code/frontend/src/components/ContextChips.tsx`

Передать: `code/frontend/src/types.ts` + `code/frontend/src/constants.ts`., `types.ts`.

Props: `incident: Incident`

Показывает inline-чипы контекста **только при выполнении условий**:

| Условие | Чип |
|---------|-----|
| `isNightTime` | 🌙 Ночная поездка 00:00–06:00 · blue |
| `continuousDrivingMin >= 120` | 🕐 {h}ч {m}мин непрерывно · amber |
| `continuousDrivingMin >= 480` | ⚠️ Превышение РТО · red |
| `speedBeforeKmh > speedLimitKmh * 1.2` | ⚡ +{delta} км/ч · orange |
| `!hasVideo` | 📷 Видео недоступно · red |

Стиль чипа: `inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs border`.

Ниже чипов — блок источников (mt-3 border-t pt-3):
```
🎥 Видеоаналитика   → hasVideo ? green "Доступно" : red "Недоступно"
📡 Телематика       → green "Активна"
🔩 CAN-шина         → green "Данные получены"
```

Экспорт: `export default ContextChips`
