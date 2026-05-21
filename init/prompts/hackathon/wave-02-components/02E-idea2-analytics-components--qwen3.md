# Волна 02E — Analytics компоненты (Идея #2, P0)
> 🤖 **Модель: `qwen/qwen3-coder:free`** | кодинг
> 💰 **Контекст:** только `src/types.ts` (~1.3K токенов) | $0
> ⚠️ Один компонент = одна сессия Cherry Studio. Строго последовательно.
> Зависит от: 01A (types), 01F-A (driver-report), 01F-B (fleet-reports), 01F-C (presets), 01F-D (fleet-vehicles)

Запускать по одному. 13 компонентов → 13 сессий.
Передавать в каждую сессию: содержимое промпта + текущий `src/types.ts`.

---

## 2E-1: VoiceQueryBox

```
Создай frontend/src/components/analytics/VoiceQueryBox.tsx

Props:
  query: string
  onChange: (q: string) => void
  onSubmit: (q: string) => void
  presets: { id: string; label: string; icon: string; query: string }[]

UI (центр экрана, max-w-[560px] mx-auto pt-20):
  📊 48px muted → «Сформируйте отчёт» (24px bold) → подзаголовок muted
  Textarea 3 строки, border rounded-lg, placeholder с примером запроса
  Строка кнопок (flex gap-2):
    [🎤] w-11 h-11 border rounded-lg
      isRecording: красная точка + «Слушаю...»
      micro-label: «faster-whisper · RU/KK/EN» (9px muted)
      onClick → startRecording()
    [→ Построить отчёт] flex-1 h-11 bg-[#1E3A8A] text-white rounded-lg
  Пресеты (flex flex-wrap gap-2 mt-6 justify-center):
    каждый: border rounded-full px-4 py-2 text-sm hover:bg-blue-50
    onClick → onChange(preset.query); onSubmit(preset.query)

startRecording():
  navigator.mediaDevices.getUserMedia({audio:true})
  → MediaRecorder → Blob → POST /api/stt → {text} → onChange(text)
  fallback: toast «Введите запрос вручную»
```

---

## 2E-2: ConfirmationModal

```
Создай frontend/src/components/analytics/ConfirmationModal.tsx

Props:
  query: string
  parsed: ParsedQuery  (из types.ts)
  onConfirm: () => void
  onRefine: () => void

UI (overlay #0F172A/30% + modal white max-w-[480px] rounded-xl shadow-2xl p-8):
  🤖 + «Вот как я понял ваш запрос» (18px bold)
  «Проверьте параметры перед построением» (13px muted)

  3 карточки параметров (mt-6 bg-slate-50 border rounded-lg p-3 flex flex-col gap-2):
    👤 «Водитель» → {parsed.driver ?? 'Весь парк'} (bold)
    📅 «Период» → {parsed.periodLabel}
    📊 «Тип данных» → badges [📹 ВА] [📡 Телематика]

  Badge уверенности (mt-2 text-sm):
    «✓ Уверенность: {Math.round(parsed.confidence * 100)}%» text-green-600

  Разделитель hr

  2 кнопки (grid grid-cols-2 gap-3):
    [✏ Уточнить запрос] ghost border h-11 rounded-lg
    [✓ Всё верно — показать] bg-[#1E3A8A] text-white h-11 rounded-lg
```

---

## 2E-3: DriverReportCard

```
Создай frontend/src/components/analytics/DriverReportCard.tsx

Props:
  report: DriverReport  (из types.ts)

UI (white border rounded-lg p-4 mb-4):
  Верхняя строка:
    Аватар 48px круглый (инициалы, bg #F8FAFC) + Имя (16px bold) + «Рейтинг: {report.score}/100»
    Progress-bar: цвет: <60 red, 60-79 yellow, ≥80 green

  grid 2 cols (mt-3 text-sm text-slate-500):
    🚛 ТС: {report.vehicleId}  |  🏷 {report.vehicleModel}
    📅 Период: {report.period}  |  📏 Пробег: {report.distanceKm} км
    ⏱ Время: {report.drivingHours}  |  🛣 Рейсов: {report.tripsCount}
    🏢 {report.division}  |  📍 {report.region}
```

---

## 2E-4: ViolationsTable

```
Создай frontend/src/components/analytics/ViolationsTable.tsx

Props:
  violations: Violation[]
  selectedId: string | null
  onSelect: (v: Violation) => void

UI (white border rounded-lg overflow-hidden):
  Thead (bg-slate-50 text-xs uppercase text-slate-500):
    # | Дата · Время | Нарушение | Источник | Серьёзность | Причина

  Tbody (каждая строка):
    cursor-pointer hover:bg-slate-50
    selectedId === v.id → bg-blue-50 border-l-4 border-[#1E3A8A]
    severity === 'gross' → border-l-4 border-red-600

    Источник: 📹 Видео (DMS) | 📡 Телематика | 📹 Видео
    Серьёзность: 🔴 Грубое | 🟡 Высокое | 🟢 Среднее
    Причина: иконка если назначена (😴📱🚗⚙), иначе «—»
```

---

## 2E-5: RouteTrackMap

```
Создай frontend/src/components/analytics/RouteTrackMap.tsx

Props:
  track: GeoJSON.FeatureCollection  (из src/data/trackPoints.ts — сконвертировать TrackPointSample[] в GeoJSON LineString)
  violations: Violation[]           (маркеры нарушений)

UI (white border rounded-lg mb-3):
  Лейбл «МАРШРУТ ЗА ПЕРИОД» (11px uppercase text-slate-500 px-4 pt-3)
  Leaflet-карта height-[220px]:
    TileLayer OpenStreetMap
    GeoJSON-слой из track (синяя полилиния, вес 3px)
    CircleMarker для каждого violation где violation.lat/lon ≠ null:
      red (#DC2626) если severity='gross'/'high', yellow (#EAB308) если 'medium'
      радиус 6px, fillOpacity 0.8
    Popup: {violation.time} · {violation.typeLabel}
  Легенда внизу: 🔴 Грубое/Высокое · 🟡 Среднее
  Если track не передан — показать «Данные маршрута недоступны», не крашиться.
```

---

## 2E-6: SpeedChart

```
Создай frontend/src/components/analytics/SpeedChart.tsx

Props:
  speedData: { time: string; speedKmh: number; alarmId: string | null }[]
             (из src/data/trackPoints.ts — TrackPointSample[], сконвертировать поле speedKmh)
  violations: Violation[]
  limitKmh: number  (из report.speedChart.speedLimitKmh, default 60)

UI (white border rounded-lg p-4):
  Лейбл «СКОРОСТЬ ЗА ПЕРИОД» (11px uppercase muted)
  Recharts LineChart height 160px:
    XAxis: time из speedData, tickFormatter: короткая дата/время
    YAxis: 0–140, domain [0, 'auto']
    Line dataKey="speed" stroke="#1E3A8A" strokeWidth=2 dot={false}
    ReferenceLine y={limitKmh} stroke="#DC2626" strokeDasharray="4 4" label="Лимит"
    ReferenceLine: вертикальные маркеры на точках где violationId !== null
    Tooltip: «{time} · {speed} км/ч»
  Если speedData пуст — показать «Нет данных о скорости», не крашиться.
```

---

## 2E-7: VideoSlidePanel

```
Создай frontend/src/components/analytics/VideoSlidePanel.tsx

Props:
  violation: Violation
  onClose: () => void

UI (white border rounded-xl shadow-xl p-4 slide-in анимация):
  Заголовок: {violation.time} · {violation.type} + Badge severity
  Кнопка × закрыть (absolute top-3 right-3)

  Видеоплеер (aspect-video bg-slate-900 rounded-lg):
    <video> если violation.videoUrl есть
    Placeholder если нет: «📷 Видео недоступно · запросить архив»
    Лейбл камеры (top-left overlay белый 11px)

  Данные (mt-3 text-sm):
    «Скорость: {speedKmh} км/ч · Лимит: {limitKmh} км/ч»
    «Превышение: +{speedKmh - limitKmh} км/ч» orange если превышение
    «Непрерывное вождение: {drivingMin} мин» chip

  Кнопка [Открыть полную карточку →] bg-[#1E3A8A] text-white mt-4 w-full rounded-lg
```

---

## 2E-8: FleetDriversList

```
Создай frontend/src/components/analytics/FleetDriversList.tsx

Props:
  drivers: FleetDriver[]  (из fleet-report.json)
  selectedId: string | null
  onSelect: (d: FleetDriver) => void

UI: список карточек-строк (flex flex-col gap-2):
  Каждая строка:
    cursor-pointer hover:bg-slate-50 border rounded-lg p-3
    selectedId === d.vehicleId → bg-blue-50 border-[#1E3A8A] border-l-4
    border-l цвет: gross_count>0 → red, violations>4 → orange, else → yellow

    Аватар 40px инициалы (bg по severity) + Имя (14px bold)
    gosNomer (12px muted) · Score-bar (100px) + число
    Badges: [📹 N] [📡 N] если > 0
    Badge [⚠️ N груб.] red если gross_count > 0
    Число нарушений (20px bold #1E3A8A) «НАРУШ.» справа
```

---

## 2E-9: FleetVehiclesList

```
Создай frontend/src/components/analytics/FleetVehiclesList.tsx

Props:
  vehicles: FleetVehicle[]  (из fleet-vehicles.json)
  selectedId: string | null
  onSelect: (v: FleetVehicle) => void

UI: список карточек (flex flex-col gap-2):
  Каждая строка (border rounded-lg p-3 cursor-pointer):
    selectedId → bg-blue-50 border-[#1E3A8A] border-l-4

    🚛 40px (bg по риску) + vehicleId (14px bold) + model (12px muted)
    Основной водитель (12px slate) · distanceKm км
    Score-bar + riskScore

    Badges VA/Tel/gross
    Camera-badge на основе cameras:
      все online → «📷 3/3 работают» bg-green-50 text-green-700
      часть offline → «📷 2/3» bg-yellow-50 text-yellow-700
      есть offline → «📷 CAM-XX offline» bg-red-50 text-red-700
    violationsCount справа (20px bold)
```

---

## 2E-10: DriverMiniDashboard

```
Создай frontend/src/components/analytics/DriverMiniDashboard.tsx

Props:
  driver: FleetDriver
  onOpenFull: () => void

UI (white border rounded-xl p-4 shadow-lg):
  Имя + госномер + Score-bar
  4 KPI: Наруш. · ВА · Тел. · Груб.
  Строки: Пробег · Рейсов · Часов
  «3 ПОСЛЕДНИХ НАРУШЕНИЯ» (11px uppercase muted):
    3 мини-строки: время + тип + severity-dot
  Кнопка [Открыть полный отчёт по {firstName} →]
    bg-[#1E3A8A] text-white w-full mt-4 rounded-lg
    onClick → onOpenFull()
```

---

## 2E-11: VehicleMiniDashboard

```
Создай frontend/src/components/analytics/VehicleMiniDashboard.tsx

Props:
  vehicle: FleetVehicle
  onOpenHistory: () => void

UI (white border rounded-xl p-4 shadow-lg):
  vehicleId (16px bold) + model (12px muted) + Score-bar

  Секция «СТАТУС КАМЕР» (mt-3):
    Для каждой камеры строка:
      📷 {cam.id} · {cam.type} · {cam.label}
      Badge: online → «● Работает» green; offline → «● Нет сигнала» red;
             degraded → «● Пониженный сигнал» yellow

  Если есть offline-камера → Banner (#FEF2F2):
    «⚠ {camId} не записывала — часть нарушений могла не зафиксироваться»

  Секция «ВОДИТЕЛИ ЗА ПЕРИОД» (mt-3):
    Для каждого driver:
      «{name}» badge [основной] если primary · «{trips} рейса · {dates}»

  3 KPI: Нарушений · Пробег км · Рейсов
  «3 ПОСЛЕДНИХ НАРУШЕНИЯ» — 3 строки
  Кнопка [Открыть историю ТС →] bg-[#1E3A8A] w-full rounded-lg
```

---

## 2E-12: FleetBarChart

```
Создай frontend/src/components/analytics/FleetBarChart.tsx

Props:
  byDay: { date: string; va: number; tel: number }[]

UI (white border rounded-lg p-4 mb-3):
  Лейбл «НАРУШЕНИЯ ПО ДНЯМ» (11px uppercase muted)
  Recharts BarChart height 160px stacked:
    Bar va fill="#7C3AED" + Bar tel fill="#0EA5E9"
    XAxis: даты, YAxis: 0–12
    Tooltip: дата + ВА N + Тел N
    Legend: [■ ВА] [■ Телематика]
```

---

## 2E-13: FleetMap

```
Создай frontend/src/components/analytics/FleetMap.tsx

Props:
  drivers: FleetDriver[]

UI (white border rounded-lg mb-3):
  Лейбл «ГЕОГРАФИЯ НАРУШЕНИЙ» (11px uppercase muted px-4 pt-3)
  Leaflet-карта height-[180px]:
    Маркеры по каждому водителю (mock координаты вокруг Москвы)
    Цвет маркера: gross_count>0 → red, violations>4 → orange, else → yellow
    Popup: имя + violations_count + «наруш.»
```
