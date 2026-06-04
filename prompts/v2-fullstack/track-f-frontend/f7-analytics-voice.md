# f7 · Аналитика + голос (`/report`)

> Трек **Frontend**. Против `00-CONTRACT.md` §3/§6 (killer-feature Оздоева) + §7.3/§7.4/§7.5/§7.8 (voice/NLU/отчёты).
> **Владеет:** `web/src/pages/Report.tsx` (**полный, заменяет scaffold из f4**), `web/src/api/voice.ts`.
> Использует voice-примитивы d5 (`VoiceButton`, `ConfirmationModal`), UI d2 (`@/components`),
> `VideoSlidePanel`/`VideoPlayer` (d2) и API-клиент f2. Идея #2. Иконки — `lucide-react`.

## Цель

Голосовая аналитика: дежурный диктует запрос → STT → NLU-разбор → подтверждение → дашборд по
водителю (В-1) или парку (В-2). Killer-feature: клик по строке нарушения раскрывает видео справа.
**Этот файл заменяет scaffold-версию `Report.tsx` из f4** — после full-scope `Report.tsx` принадлежит f7
(см. §7.7). Маршрут `/report` (f1).

## Поток (идея #2)

1. **`VoiceButton`** (d5) — запись микрофона, состояния `idle/recording/processing`. По остановке отдаёт
   `Blob` через `onRecorded`.
2. **`POST /api/reports/transcribe`** (§7.4, `multipart/form-data` wav) → `{text, lang, confidence}`.
   Текст показать в поле ввода (его можно отредактировать руками — текстовый ввод как альтернатива голосу).
3. **`POST /api/reports/query`** (§7.4) → `{query: ReportQuery, report: DriverReport|FleetReport}`.
   `ReportQuery` — §7.5.
4. **`ConfirmationModal`** (d5) «Вот как я понял ваш запрос» с распарсенным `ReportQuery`:
   `[Исправить]` (вернуть в поле текста) / `[✓ Показать]` (рендер дашборда).
5. **Дашборд**:
   - **В-1 (driver)** — `DriverReport`: KPI-плашки + `DataTable` нарушений по водителю/ТС.
   - **В-2 (fleet)** — `FleetReport`: KPI + toggle представления **«По водителям» | «По ТС»**
     (соответствует `ReportQuery.view = 'drivers'|'vehicles'`; режим «По ТС» может тянуть
     `client.getVehicleReport(plate)` → `VehicleReport` §7.5 для детализации ТС).

## Killer feature — видео справа (§6)

- Клик по строке нарушения (`IncidentSummary`/нарушение из отчёта) → **`VideoSlidePanel`** (выезжает справа)
  с `VideoPlayer`.
- Источник видео по типу нарушения: **`cam_dms_url` (ch5) для DMS-нарушений**, **`cam_front_url` (ch1)
  для ADAS** (см. §6). URL берётся из `IncidentDetail` (`client.getIncident(id)`) либо
  `client.videoUrl(id, channel)`; канал — 5 для DMS, 1 для ADAS.
- Если `video_available===false` — пустое состояние панели + «Запросить архив».

## `web/src/api/voice.ts`

- Тонкий слой записи/отправки аудио поверх f2-клиента (НЕ переписывает `client.ts`):
  - запись/получение `Blob` приходит из `VoiceButton` (MediaRecorder там, d5);
  - `transcribe(blob: Blob, lang?) → {text, lang, confidence}` — собирает `FormData` (`multipart/form-data`,
    поле wav) и шлёт `POST /api/reports/transcribe`. Если браузер отдал webm/opus — слать с корректным MIME,
    перекодировку оставить бэку (контракт b8).
  - `queryReport(text) → {query, report}` — обёртка над `POST /api/reports/query` (либо реэкспорт метода f2).
- Уважает флаг `VITE_USE_FIXTURES`: при `true` — детерминированный mock transcribe/query без сети/микрофона.

## Зависимости и параллельность

- Зависит от: **d5** (`VoiceButton`, `ConfirmationModal`), **d2** (`DataTable`, `VideoPlayer`,
  `VideoSlidePanel`, KPI/`Card`), **f2/x2** (см. ниже). Маршрут — f1.
- **Дозависимость f2/x2:** f2-клиент дополнить методами **`transcribe`**, **`queryReport`** (новая форма
  `{query, report}` по §7.4), **`getVehicleReport(plate)`** (`GET /api/reports/vehicle/{plate}`) и типами
  `ReportQuery`/`VehicleReport`/`DriverRef` (§7.5). До их готовности `voice.ts` ходит напрямую/на фикстурах.
- Параллелится с f5/f6/f8 (разные файлы). Конфликт владения только с f4-scaffold `Report.tsx` — замещается.

## Check

- `/report` открывается на живом API и на фикстурах (`VITE_USE_FIXTURES=true`).
- 🎤 → запись → `transcribe` → текст появляется в поле; текст можно отредактировать вручную.
- Текст → `query` → `ConfirmationModal` показывает `ReportQuery`; `[Исправить]`/`[✓ Показать]` работают.
- Дашборд В-1 (driver) и В-2 (fleet) рендерятся; в fleet toggle «По водителям|По ТС» переключает представление.
- Клик по нарушению открывает `VideoSlidePanel` справа: **DMS → `cam_dms_url` (ch5)**, **ADAS → `cam_front_url` (ch1)**.
- Нарушение без видео показывает пустое состояние + «Запросить архив».
- Файл полностью заменяет scaffold `Report.tsx` из f4.
