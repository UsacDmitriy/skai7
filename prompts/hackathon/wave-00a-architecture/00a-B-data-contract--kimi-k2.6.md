# Волна 00a-B — Data Contract (TypeScript интерфейсы)
> 🤖 **Модель: `moonshotai/kimi-k2.6`** | точное соответствие типов и данных
> 💰 **Контекст: 2 JSON-файла** (~5K токенов, ~$0.02)
> ❌ НЕ читать fleet-report.json сразу — он пустой (0 bytes)
> ⚠️ Запускать после 00a-A. Результат → черновик `src/types.ts`

## Что передать в сессию

Вставить текстом (именно в таком порядке — от меньшего к большему):
1. `data/mock/driver-report.json` (~4K токенов)
2. `data/mock/incidents.json` (~12K токенов)
3. Раздел "Дерево компонентов" из `hackathon/context/TECH-DESIGN.md` (~2K токенов)

> fleet-report.json сейчас пустой — пропустить.
> incidents.json — самый тяжёлый файл, но необходим.

---

## Промпт

```
Перед тобой mock JSON-данные для SKAI Unified Incident Window.

Задача: написать `src/types.ts` — полный файл TypeScript-интерфейсов.

Правила:
1. Каждое поле из JSON → в интерфейс. Не угадывать — только то что есть в данных.
2. String-literal unions для перечислимых полей:
   alarm_type: 'DMS_DROWSY' | 'CRASH_SENSOR' | 'DMS_PHONE' | 'HARSH_BRAKING' | 'DRIVER_SUBSTITUTION'
3. Optional (?): только если поле отсутствует в части записей JSON.
4. Один JSDoc-комментарий на каждый интерфейс (одна строка).
5. Props из дерева компонентов — добавить как отдельные интерфейсы.

Включить:
Incident, TelemetryPoint, VideoClip, Source, Driver, Vehicle,
DriverReport, Violation, RoutePoint, SpeedPoint,
Ticket, KPIStats, QueryResult, AppContextType,
AlarmType, IncidentStatus, ActionType, SourceType

Только код файла src/types.ts. Без объяснений.
```
