# d5 · Voice-кнопка, окно подтверждения, Timeline

> Трек **Design**. Против `00-CONTRACT.md` §4 (токены) + §7.6 (добавки voice/timeline) + §7.7 (владение d5).
> **Модель:** 🔴 Opus — высокие ставки: интеграция / синк / алгоритм / анти-регресс / killer-feature / барьер.
> **Владеет:** `web/src/components/ui/VoiceButton.tsx`, `web/src/components/ui/ConfirmationModal.tsx`,
> `web/src/components/ui/Timeline.tsx`. Зависит от d1 (токены) и d2 (Button/SeverityBadge).
> Иконки — `lucide-react`.

## Цель

Презентационные примитивы для голосового отчёта (`/report`, идея #2) и видеодосье (`/trip/:id`, идея #7):
кнопка записи голоса, окно подтверждения распарсенного запроса и таймлайн событий трека. Запись звука
ведётся внутри `VoiceButton` (MediaRecorder), но NLU/STT/fetch — снаружи (f7). Только props → разметка
плюс захват аудио наружу через callback.

## Компоненты

1. **`VoiceButton.tsx`** — кнопка записи голоса, три состояния (§7.6).
   - Props: `state: 'idle' | 'recording' | 'processing'`, `onRecorded: (blob: Blob) => void`,
     `disabled?`, `onStart?`, `onStop?`.
   - **Состояния (рендер обязателен во всех трёх):**
     - `idle` — стиль **primary-outline** (обводка `primary` #1E3A8A, прозрачный фон), иконка 🎤 (`Mic`).
     - `recording` — **critical-pulse**: фон `critical` (#DC2626), пульсирующая анимация (CSS `animate-pulse`
       или keyframes-кольцо), иконка `Square`/`MicOff`, индикатор записи.
     - `processing` — **primary spinner**: `primary` + крутящийся `Loader2`, кнопка disabled.
   - **Запись WAV:** через `MediaRecorder` (`getUserMedia({audio:true})`); по остановке формирует `Blob`
     (WAV; если браузер пишет webm/opus — отдать как есть с корректным MIME, контракт `transcribe` —
     multipart wav, перекодировку оставить f7/бэку) и вызывает `onRecorded(blob)`. Поток микрофона
     закрывается после стопа (release tracks).
   - Презентационный контракт: внешнее `state` управляет видом; внутренний MediaRecorder только пишет
     и отдаёт blob наружу. NLU не трогает.

2. **`ConfirmationModal.tsx`** — окно «Вот как я понял ваш запрос».
   - Props: `open: boolean`, `query: ReportQuery`, `onEdit: () => void`, `onConfirm: () => void`,
     `onClose?`. `ReportQuery` — из контракта §7.5
     (`{ kind, plate?, driver_name?, period_days?, view? }`).
   - Заголовок «Вот как я понял ваш запрос». Тело — человекочитаемые параметры `ReportQuery`
     (тип отчёта driver/fleet, ФИО/госномер, период «за N дней», представление drivers/vehicles).
   - Кнопки (d2 `Button`): **[Исправить]** (`secondary` → `onEdit`) и **[✓ Показать]**
     (`primary` → `onConfirm`). Скругление модала `xl` (12px), overlay `ink`/затемнение.

3. **`Timeline.tsx`** — таймлайн событий трека (видеодосье #7).
   - Props: `events: TimelineEvent[]`, `onSelect?: (e: TimelineEvent) => void`.
     `TimelineEvent { ts_offset: number, alarm_code: string, label: string, severity: Severity, has_video: boolean }`.
   - Горизонтальная **линия трека `#1E3A8A`** (`primary`). Точки-события на линии по `ts_offset`,
     цвет точки — **по severity** (маппинг d1: critical/high/warning/ok).
   - Маркер **`t=0`** (`ts_offset===0`) — выделенный, цвет `critical` (#DC2626), крупнее остальных.
   - Значок видео (`Video`/`VideoOff` Lucide) у точек с `has_video`. Клик по точке → `onSelect(e)`.
   - Подписи времени — `tabular-nums`. Только presentation: видео момента подставляет f10 по callback.

## Требования

- TypeScript, строгие props-интерфейсы, именованный экспорт.
- Иконки — `lucide-react`.
- Никаких прямых hex в разметке — Tailwind-классы/CSS-переменные d1 (severity-маппинг d1:
  medium→warning, low→ok). Допустимые литералы только там, где значение задаёт §7.6 и его заводит d1.
- `VoiceButton` и `Timeline` рендерятся в витрине d3 во всех состояниях.

## Граничные данные (рендер без падения)

- `Timeline events=[]` — рендерит линию трека без точек (без падения), без «t=0»-маркера если нет события с `ts_offset===0`.
- Точки с одинаковым `ts_offset` (наложение) — раскладываются без NaN/деления на ноль при единственной точке (диапазон=0 → точка в начале/центре, без краша масштабирования).
- `ts_offset` вне ожидаемого диапазона/отрицательный — клампится в пределы линии, не уезжает за контейнер.
- Неизвестный `severity` — фолбэк-цвет точки, без падения маппинга.
- **Курсор-плейхед** (`playheadOffset`, если передаётся опционально): сдвигает курсор по линии; вне диапазона/`undefined` — курсор скрыт, Timeline рендерится штатно. (Контракт: движущийся `playheadOffset` — §243; не ломать существующий props-контракт.)
- `VoiceButton`: отказ `getUserMedia` (нет разрешения/нет устройства) — не падает, остаётся в визуально валидном состоянии (внешнее `state` управляет видом), поток не висит.

## Check

- Все 3 файла компилируются (`tsc --noEmit`) без ошибок типов.
- `VoiceButton` рендерится во **всех трёх** состояниях (idle primary-outline / recording critical-pulse /
  processing spinner); по остановке записи вызывает `onRecorded` с `Blob`; поток микрофона освобождается;
  отказ `getUserMedia` обработан без падения.
- `ConfirmationModal` показывает все поля `ReportQuery` человекочитаемо; **[Исправить]** вызывает `onEdit`,
  **[✓ Показать]** — `onConfirm`; при `open=false` не рендерится.
- `Timeline`: линия трека `#1E3A8A`; точки окрашены по severity (маппинг d1, неизвестный → фолбэк); маркер
  `t=0` — `critical` и визуально выделен; клик по точке вызывает `onSelect`; значок видео виден у `has_video`;
  `events=[]` и единственная точка (диапазон=0) — рендер без падения; курсор `playheadOffset` (если есть) двигается, вне диапазона скрыт.
- a11y: точка таймлайна и `VoiceButton` фокусируемы и активируются с клавиатуры (Enter/Space); `VoiceButton`
  имеет доступное имя и `aria-pressed`/`aria-busy` по состоянию; статус записи доступен скринридеру (не только цвет/пульс).

## Коммит (обязательно)

Заверши промпт коммитом в свою ветку — **merge на барьере берёт только коммиты**; незакоммиченная
работа в worktree на барьер не попадёт:

```bash
git add -A && git commit -m "d5: <что сделано>"
```
