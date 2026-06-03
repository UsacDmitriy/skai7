# DESIGN.md — Дизайн-система SKAI Online

> Используй этот файл при генерации UI в Stitch или Claude Design.
> Все экраны должны соответствовать этой системе.

## Colors

```
Primary:      #1E3A8A  (SKAI синий акцент)
Primary-dark: #1E3070  (hover состояния)
Primary-50:   #EFF6FF  (светлый фон активного элемента)
Background:   #F8FAFC  (страница)
Surface:      #FFFFFF  (карточки, панели)
Text:         #0F172A  (основной)
Text-muted:   #64748B  (вторичный, подписи)
Border:       #E2E8F0  (разделители, рамки)
Border-focus: #1E3A8A  (фокус на input)

Severity Critical: #DC2626  bg: #FEE2E2  text: #991B1B
Severity High:     #EA580C  bg: #FEF3C7  text: #B45309
Severity Warning:  #EAB308  bg: #FEF9C3  text: #854D0E
Severity OK:       #16A34A  bg: #DCFCE7  text: #166534

Score bar fill:    linear-gradient(90deg, #16A34A 0%, #EAB308 50%, #DC2626 100%)
```

## Typography

```
Font family: Inter, -apple-system, BlinkMacSystemFont, sans-serif
Numbers (tabular): font-variant-numeric: tabular-nums

H1:       32px / 700 / 1.2
H2:       24px / 600 / 1.3
H3:       18px / 600 / 1.4
Body:     14px / 400 / 1.6
Body-sm:  13px / 400 / 1.6
Caption:  12px / 500 / 1.4  (uppercase + letter-spacing: 0.5px для меток)
```

## Spacing

```
Base unit: 4px
xs: 4px   sm: 8px   md: 16px   lg: 24px   xl: 32px   2xl: 48px
Card padding: 16px (sm карточки) / 20-24px (стандарт)
Table cell padding: 8-10px vertical, 10-12px horizontal
Section gap: 16-20px между блоками
```

## Components

### Боковое меню SKAI
```
Width: 48px (свёрнуто) / 240px (развёрнуто, при hover)
Background: #FFFFFF
Border-right: 1px solid #E2E8F0
Icons: 20-22px, цвет #64748B (неактивные), #1E3A8A (активные)
Активный пункт: background #EFF6FF, border-left 3px solid #1E3A8A
Группы разделены небольшими заголовками (12px, uppercase, #64748B)

Пункты меню:
  МОНИТОРИНГ
    📍 Карта
    🛡 Мониторинг безопасности   ← новый
  ВИДЕОАНАЛИТИКА
    📋 События
    📡 Прямая трансляция
    🎬 Видеоархив
    ⬇ Загрузки
    ✓ Блок валидации
    🔔 Блок реагирования
  ДАШБОРДЫ И ОТЧЁТЫ
    📊 Дашборды
    📄 Отчёты
    ⚡ Быстрый отчёт            ← новый (NEW badge)
  ПАРК
    🏥 Здоровье парка            ← новый
```

### Header bar (верхняя строка)
```
Height: 56px
Background: #FFFFFF
Border-bottom: 1px solid #E2E8F0
Shadow: 0 1px 3px rgba(0,0,0,0.08)
Содержит: logo + статус-строка + счётчики
```

### Severity badge
```
Inline-flex, align-center, gap 6px
Padding: 2px 8px 2px 6px
Border-radius: 12px
Font: 12px / 500
Icon: 6px цветной кружок

Critical: bg #FEE2E2, text #991B1B, dot #DC2626
High:     bg #FEF3C7, text #B45309, dot #EA580C
Warning:  bg #FEF9C3, text #854D0E, dot #EAB308
OK:       bg #DCFCE7, text #166534, dot #16A34A
```

### Карточка инцидента (в ленте)
```
Background: #FFFFFF
Border: 1px solid #E2E8F0
Border-left: 4px solid <severity-color>
Border-radius: 6px
Padding: 12px 16px
Cursor: pointer
Hover: box-shadow 0 2px 6px rgba(30,58,138,0.10), border-color #1E3A8A
Selected: background #EFF6FF, border-color #1E3A8A
```

### Score bar
```
Background: #E2E8F0
Height: 4px
Border-radius: 2px
Fill: gradient от зелёного к красному
Числовое значение: 14px / 700 / #0F172A, справа
```

### Кнопки
```
Primary:   bg #1E3A8A, text white, hover bg #1E3070
Secondary: bg white, border #E2E8F0, text #0F172A, hover border #1E3A8A
Danger:    bg #DC2626, text white, hover bg #B91C1C
Ghost:     bg transparent, text #64748B, hover bg #F8FAFC

Size: height 36px, padding 8px 16px, border-radius 6px, font 14px/500
Icon button: 36×36px, border-radius 6px
```

### Видео-плеер (SKAI стиль)
```
Aspect ratio: 16:9
Background: #0F172A
Controls (нижняя полоска):
  ▶/⏸  ⏪  ⏩  прогресс-бар  время  🔊  ⛶  ⋮
Progress bar: height 3px, filled #1E3A8A, cursor pointer для скраба
Метка события: вертикальная линия #EAB308 на прогресс-баре
Border-radius: 4px (встроенный) / 8px (полноэкранный)
```

### Таблица (SKAI стиль)
```
Header: bg #F8FAFC, border-bottom 2px solid #E2E8F0, font 12px/600/uppercase
Rows: border-bottom 1px solid #F1F5F9
Hover: bg #F8FAFC
Active/selected: bg #EFF6FF
Sort icon: ↑↓ в заголовке
```

### График телеметрии (Recharts)
```
Background: white
Grid: stroke #E2E8F0, strokeDasharray 2px
Axis: stroke #94A3B8, fontSize 11
Line Скорость: stroke #1E3A8A, strokeWidth 2
Line Акселерометр: stroke #EA580C, strokeWidth 1.5
Событие-метка: ReferenceLine, stroke #EAB308, strokeDasharray 4
Tooltip: bg white, border 1px solid #E2E8F0, border-radius 6px, shadow
```

### Модальное окно
```
Overlay: rgba(0,0,0,0.3), backdrop-filter blur(4px)
Modal: bg white, border-radius 12px, max-width 560px, padding 24px
Header: font 16px/700, close button top-right
Footer: flex, justify-end, gap 8px
```

### Progress bar (генерация отчёта)
```
Track: bg #E2E8F0, height 8px, border-radius 4px
Fill: bg #1E3A8A, animated shimmer при загрузке
Текст под баром: 12px, #64748B
```

## Иконки

Использовать Lucide React:
- Видеоаналитика: Video, Film, Camera
- Телематика: Activity, Gauge, Navigation
- Действия: Phone, Check, X, AlertTriangle, Download
- Навигация: ChevronRight, ArrowLeft
- Статусы: AlertCircle, CheckCircle, XCircle, Info
- Меню: Map, BarChart2, FileText, Zap, Heart

## Анимации

```
transition: all 150ms ease (кнопки, hover)
transition: opacity 200ms ease (появление панелей)
Skeleton loading: bg linear-gradient(...), animation pulse 1.5s infinite
New item pulse: animation ping 1s ease-in-out (новый инцидент в ленте)
```
